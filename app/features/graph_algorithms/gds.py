"""Algoritmos de grafo (Neo4j GDS) sobre o grafo Order/Product/Customer já
projetado por `order/graph_sync.py`.

- Leiden em vez de Louvain (comunidades sempre conectadas, mais estável).
- FastRP + KNN em vez de Node Similarity puro (escala melhor em catálogos
  grandes — Node Similarity puro é O(n^2) na vizinhança). KNN combina o
  `structuralEmbedding` do FastRP (sinal de "comprado junto", via `CONTAINS`)
  com o `text_embedding` já gerado por `embeddings/pipeline.py` (sinal de
  "descrito de forma parecida") — sem isso, `SIMILAR_TO` só captura
  co-ocorrência de compra e ignora produtos parecidos que nunca foram
  comprados juntos (ex: dois vestidos florais de fornecedores diferentes).
- Padrão mutate -> validar -> write: o resultado só é persistido no grafo
  principal depois de passar por um check de qualidade (ex: modularity).
- Pensado para rodar como job agendado (cron/Airflow) via
  `run_all_batch_algorithms`, não a cada ingestão — `graph_algorithms/router.py`
  expõe isso como um trigger assíncrono (mesmo padrão de
  `order/router.py::trigger_graph_sync`), não uma chamada síncrona bloqueante.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.infrastructure.database.neo4j import run_query
from app.core.logger import logger

PRODUCT_GRAPH = "produtos-coocorrencia"
CUSTOMER_GRAPH = "clientes-produtos"

# Modularity mínima aceitável para persistir o resultado do Leiden.
# Abaixo disso, as comunidades não têm estrutura real e não deveriam
# ser gravadas (indicativo de dado insuficiente ou muito ruidoso).
MIN_MODULARITY_THRESHOLD = 0.1

DEFAULT_ASSOCIATION_MIN_SUPPORT_COUNT = 2
DEFAULT_ASSOCIATION_MIN_CONFIDENCE = 0.05


def _drop_graph_if_exists(graph_name: str) -> None:
    run_query("CALL gds.graph.drop($name, false)", {"name": graph_name})


def _record_run(name: str, **details: object) -> None:
    """Marca quando cada algoritmo rodou por último, num nó `AlgorithmRun`
    dedicado (não uma propriedade em cada nó tocado — mais barato de
    escrever e dá um único lugar pra consultar "quando isso rodou por
    último"). Como o schema exposto ao `GraphCypherQAChain` (via
    `rag/cypher_qa.py`'s `enhanced_schema=True`) é lido diretamente do banco,
    o LLM da via GLOBAL já consegue responder "quando a segmentação rodou
    pela última vez" sem nenhum código novo do lado do RAG — só precisa que
    esse nó exista."""
    run_query(
        "MERGE (run:AlgorithmRun {name: $name}) SET run.computed_at = datetime(), run += $details",
        {"name": name, "details": details},
    )


def _product_embedding_count() -> int:
    result = run_query(
        """
        MATCH (p:Product)
        WHERE p.text_embedding IS NOT NULL
        RETURN count(p) AS count
        """
    )
    return int(result[0]["count"]) if result else 0


def _project_product_graph() -> None:
    """Projeta `text_embedding` junto com a topologia, com um vetor de zeros
    como `defaultValue` para nós que ainda não passaram por
    `embeddings/pipeline.py` (ou para quando ele nunca rodou) — sem isso o
    KNN falharia exigindo a propriedade em todo nó do grafo projetado. Um nó
    sem embedding real só perde o sinal semântico nessa rodada (fica só com
    o estrutural do FastRP), não quebra o job."""
    _drop_graph_if_exists(PRODUCT_GRAPH)
    zero_embedding = [0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS
    run_query(
        f"""
        CALL gds.graph.project(
          '{PRODUCT_GRAPH}', ['Order', 'Product'],
          {{CONTAINS: {{orientation: 'UNDIRECTED'}}}},
          {{nodeProperties: {{text_embedding: {{defaultValue: $zero_embedding}}}}}}
        )
        """,
        {"zero_embedding": zero_embedding},
    )
    logger.info("graph_projected", graph=PRODUCT_GRAPH)


def _project_customer_graph() -> None:
    _drop_graph_if_exists(CUSTOMER_GRAPH)
    run_query(
        f"""
        CALL gds.graph.project(
          '{CUSTOMER_GRAPH}', ['Customer', 'Order', 'Product'],
          {{
            PLACED_BY: {{orientation: 'UNDIRECTED'}},
            CONTAINS: {{orientation: 'UNDIRECTED'}}
          }}
        )
        """
    )
    logger.info("graph_projected", graph=CUSTOMER_GRAPH)


def run_product_similarity() -> None:
    """FastRP (embedding estrutural) + KNN aproximado — escala para catálogos
    grandes. KNN combina `structuralEmbedding` (FastRP, sinal de compra) com
    `text_embedding` (OpenAI, sinal semântico) — cada propriedade entra com
    sua própria similaridade de cosseno e o GDS normaliza e combina as duas
    num único score por par, em vez de escolher uma ou outra."""
    _project_product_graph()

    run_query(
        f"""
        CALL gds.fastRP.mutate('{PRODUCT_GRAPH}', {{
          embeddingDimension: 128,
          mutateProperty: 'structuralEmbedding',
          randomSeed: 42
        }})
        """
    )
    logger.info("fastrp_computed", graph=PRODUCT_GRAPH)

    node_properties = "[{structuralEmbedding: 'COSINE'}]"
    embedding_count = _product_embedding_count()
    if embedding_count > 0:
        node_properties = "[{structuralEmbedding: 'COSINE'}, {text_embedding: 'COSINE'}]"

    result = run_query(
        f"""
        CALL gds.knn.mutate('{PRODUCT_GRAPH}', {{
          nodeProperties: {node_properties},
          mutateRelationshipType: 'SIMILAR_TO',
          mutateProperty: 'score',
          topK: 5,
          sampleRate: 1.0
        }})
        YIELD nodesCompared, relationshipsWritten
        """
    )
    logger.info(
        "knn_computed",
        graph=PRODUCT_GRAPH,
        result=result,
        embeddings_used=embedding_count > 0,
    )

    # Persiste no banco principal só depois do cálculo confirmado em memória.
    run_query(f"CALL gds.graph.relationship.write('{PRODUCT_GRAPH}', 'SIMILAR_TO', 'score')")
    _record_run("product_similarity")
    logger.info("product_similarity_persisted")


def run_product_pagerank() -> None:
    """PageRank global — importância estrutural do produto na rede de compras."""
    run_query(
        f"""
        CALL gds.pageRank.write('{PRODUCT_GRAPH}', {{
          writeProperty: 'pagerank'
        }})
        """
    )
    _record_run("product_pagerank")
    logger.info("pagerank_persisted", graph=PRODUCT_GRAPH)


def run_customer_segmentation() -> dict:
    """Leiden para segmentação de clientes — só persiste se modularity for aceitável."""
    _project_customer_graph()

    result = run_query(
        f"""
        CALL gds.leiden.mutate('{CUSTOMER_GRAPH}', {{
          mutateProperty: 'community'
        }})
        YIELD communityCount, modularity
        """
    )[0]

    modularity = result["modularity"]
    logger.info(
        "leiden_computed",
        graph=CUSTOMER_GRAPH,
        community_count=result["communityCount"],
        modularity=modularity,
    )

    if modularity < MIN_MODULARITY_THRESHOLD:
        logger.warning(
            "leiden_modularity_too_low_skipping_write",
            modularity=modularity,
            threshold=MIN_MODULARITY_THRESHOLD,
        )
        return {"persisted": False, **result}

    run_query(f"CALL gds.graph.nodeProperties.write('{CUSTOMER_GRAPH}', ['community'])")
    _record_run(
        "customer_segmentation", community_count=result["communityCount"], modularity=modularity
    )
    logger.info("customer_segmentation_persisted")
    return {"persisted": True, **result}


def run_customer_rfm() -> dict:
    """Calcula RFM explicavel por cliente e grava no proprio no `Customer`.

    Os thresholds sao absolutos de partida, adequados enquanto o volume ainda
    e pequeno. Quando houver historico maior, esta funcao pode evoluir para
    pontuacao por percentis sem mudar o contrato consumido pelas APIs/RAG.
    """
    result = run_query(
        """
        MATCH (c:Customer)<-[:PLACED_BY]-(o:Order)
        WITH
          c,
          count(DISTINCT o) AS frequency,
          sum(coalesce(o.total_value, 0.0)) AS monetary,
          max(o.created_at) AS last_order_at
        WITH
          c,
          frequency,
          monetary,
          last_order_at,
          CASE
            WHEN last_order_at IS NULL THEN 9999
            ELSE duration.inDays(date(last_order_at), date()).days
          END AS recency_days
        WITH
          c,
          frequency,
          monetary,
          last_order_at,
          recency_days,
          CASE
            WHEN recency_days <= 30 THEN 5
            WHEN recency_days <= 60 THEN 4
            WHEN recency_days <= 90 THEN 3
            WHEN recency_days <= 180 THEN 2
            ELSE 1
          END AS recency_score,
          CASE
            WHEN frequency >= 10 THEN 5
            WHEN frequency >= 5 THEN 4
            WHEN frequency >= 3 THEN 3
            WHEN frequency >= 2 THEN 2
            ELSE 1
          END AS frequency_score,
          CASE
            WHEN monetary >= 5000 THEN 5
            WHEN monetary >= 2500 THEN 4
            WHEN monetary >= 1000 THEN 3
            WHEN monetary >= 500 THEN 2
            ELSE 1
          END AS monetary_score
        WITH
          c,
          frequency,
          monetary,
          last_order_at,
          recency_days,
          recency_score,
          frequency_score,
          monetary_score,
          recency_score + frequency_score + monetary_score AS rfm_score
        SET
          c.rfm_recency_days = recency_days,
          c.rfm_frequency = frequency,
          c.rfm_monetary = monetary,
          c.rfm_recency_score = recency_score,
          c.rfm_frequency_score = frequency_score,
          c.rfm_monetary_score = monetary_score,
          c.rfm_score = rfm_score,
          c.last_order_at = last_order_at,
          c.rfm_segment = CASE
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4
              THEN 'campeoes'
            WHEN recency_score >= 4 AND frequency_score >= 3
              THEN 'leais'
            WHEN recency_score >= 4 AND frequency_score <= 2
              THEN 'novos'
            WHEN recency_score <= 2 AND frequency_score >= 3
              THEN 'em_risco'
            WHEN recency_score <= 2 AND frequency_score <= 2
              THEN 'hibernando'
            ELSE 'potencial'
          END
        RETURN count(c) AS customers_scored
        """
    )
    payload = result[0] if result else {"customers_scored": 0}
    _record_run("customer_rfm", **payload)
    logger.info("customer_rfm_persisted", result=payload)
    return payload


def run_association_rules(
    min_support_count: int = DEFAULT_ASSOCIATION_MIN_SUPPORT_COUNT,
    min_confidence: float = DEFAULT_ASSOCIATION_MIN_CONFIDENCE,
) -> dict:
    """Calcula regras direcionais produto -> produto via pedidos compartilhados."""
    result = run_query(
        """
        MATCH (o:Order)-[:CONTAINS]->(:Product)
        WITH count(DISTINCT o) AS total_orders
        MATCH (a:Product)<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(b:Product)
        WHERE a.id <> b.id
        WITH total_orders, a, b, count(DISTINCT o) AS pair_orders
        MATCH (a)<-[:CONTAINS]-(ao:Order)
        WITH total_orders, a, b, pair_orders, count(DISTINCT ao) AS a_orders
        MATCH (b)<-[:CONTAINS]-(bo:Order)
        WITH total_orders, a, b, pair_orders, a_orders, count(DISTINCT bo) AS b_orders
        WITH
          total_orders,
          a,
          b,
          pair_orders,
          a_orders,
          b_orders,
          toFloat(pair_orders) / total_orders AS support,
          toFloat(pair_orders) / a_orders AS confidence,
          (toFloat(pair_orders) / total_orders) /
            ((toFloat(a_orders) / total_orders) * (toFloat(b_orders) / total_orders)) AS lift
        WHERE pair_orders >= $min_support_count
          AND confidence >= $min_confidence
        MERGE (a)-[r:BOUGHT_WITH]->(b)
        SET
          r.support_count = pair_orders,
          r.support = support,
          r.confidence = confidence,
          r.lift = lift,
          r.updated_at = datetime()
        RETURN count(r) AS rules_written
        """,
        {
            "min_support_count": min_support_count,
            "min_confidence": min_confidence,
        },
    )
    payload = result[0] if result else {"rules_written": 0}
    payload["min_support_count"] = min_support_count
    payload["min_confidence"] = min_confidence
    _record_run("association_rules", **payload)
    logger.info("association_rules_persisted", result=payload)
    return payload


def run_personalized_pagerank(product_ids: list[str], limit: int = 10) -> list[dict]:
    """
    PageRank personalizado — usado em tempo real (via API/retriever), não em
    batch. Recebe os `Product.id` de domínio (ex: produtos que o cliente já
    comprou), resolve para os nós internos do grafo já projetado e retorna
    ranking contextual, não o ranking global.

    Resolução + stream em uma única query (1 round-trip) em vez de buscar os
    node ids internos numa chamada separada.
    """
    return run_query(
        f"""
        MATCH (p:Product) WHERE p.id IN $product_ids
        WITH collect(p) AS sourceNodes
        CALL gds.pageRank.stream('{PRODUCT_GRAPH}', {{sourceNodes: sourceNodes}})
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        RETURN node.id AS product_id, node.name AS product_name, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"product_ids": product_ids, "limit": limit},
    )


def recommend_by_product(product_id: str, limit: int = 10) -> list[dict]:
    return run_query(
        """
        MATCH (seed:Product {id: $product_id})
        CALL {
          WITH seed
          MATCH (seed)-[s:SIMILAR_TO]->(p:Product)
          RETURN
            p,
            coalesce(s.score, 0.0) AS similarity_score,
            0.0 AS association_score,
            0 AS support_count,
            0.0 AS confidence,
            0.0 AS lift,
            ['similaridade'] AS reasons
          UNION
          WITH seed
          MATCH (seed)-[b:BOUGHT_WITH]->(p:Product)
          RETURN
            p,
            0.0 AS similarity_score,
            coalesce(b.lift, 0.0) AS association_score,
            coalesce(b.support_count, 0) AS support_count,
            coalesce(b.confidence, 0.0) AS confidence,
            coalesce(b.lift, 0.0) AS lift,
            ['comprado_junto'] AS reasons
        }
        WITH
          p,
          max(similarity_score) AS similarity_score,
          max(association_score) AS association_score,
          max(support_count) AS support_count,
          max(confidence) AS confidence,
          max(lift) AS lift,
          reduce(acc = [], reason_list IN collect(reasons) | acc + reason_list) AS all_reasons
        WITH
          p,
          similarity_score,
          association_score,
          support_count,
          confidence,
          lift,
          [reason IN all_reasons WHERE reason IS NOT NULL] AS reasons,
          (similarity_score * 0.55) +
            (CASE WHEN lift > 0 THEN lift ELSE 0 END * 0.30) +
            (coalesce(p.pagerank, 0.0) * 0.15) AS score
        RETURN
          p.id AS product_id,
          p.name AS product_name,
          p.code AS product_code,
          score,
          reasons,
          similarity_score,
          support_count,
          confidence,
          lift,
          p.pagerank AS pagerank
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"product_id": product_id, "limit": limit},
    )


def recommend_by_customer(customer_id: str, limit: int = 10) -> list[dict]:
    return run_query(
        """
        MATCH (c:Customer {id: $customer_id})
        OPTIONAL MATCH (c)<-[:PLACED_BY]-(:Order)-[:CONTAINS]->(owned:Product)
        WITH c, collect(DISTINCT owned.id) AS owned_product_ids, collect(DISTINCT owned) AS owned
        CALL {
          WITH owned
          UNWIND owned AS seed
          WITH seed WHERE seed IS NOT NULL
          MATCH (seed)-[s:SIMILAR_TO]->(p:Product)
          RETURN
            p,
            coalesce(s.score, 0.0) AS similarity_score,
            0.0 AS association_score,
            0 AS support_count,
            0.0 AS confidence,
            0.0 AS lift,
            ['similar_ao_historico'] AS reasons
          UNION
          WITH owned
          UNWIND owned AS seed
          WITH seed WHERE seed IS NOT NULL
          MATCH (seed)-[b:BOUGHT_WITH]->(p:Product)
          RETURN
            p,
            0.0 AS similarity_score,
            coalesce(b.lift, 0.0) AS association_score,
            coalesce(b.support_count, 0) AS support_count,
            coalesce(b.confidence, 0.0) AS confidence,
            coalesce(b.lift, 0.0) AS lift,
            ['comprado_junto_ao_historico'] AS reasons
        }
        WITH
          c,
          owned_product_ids,
          p,
          max(similarity_score) AS similarity_score,
          max(association_score) AS association_score,
          max(support_count) AS support_count,
          max(confidence) AS confidence,
          max(lift) AS lift,
          reduce(acc = [], reason_list IN collect(reasons) | acc + reason_list) AS all_reasons
        WHERE NOT p.id IN owned_product_ids
        WITH
          c,
          p,
          similarity_score,
          association_score,
          support_count,
          confidence,
          lift,
          [reason IN all_reasons WHERE reason IS NOT NULL] AS reasons,
          (similarity_score * 0.45) +
            (CASE WHEN lift > 0 THEN lift ELSE 0 END * 0.35) +
            (coalesce(p.pagerank, 0.0) * 0.10) +
            (coalesce(c.rfm_score, 0) * 0.02) AS score
        RETURN
          p.id AS product_id,
          p.name AS product_name,
          p.code AS product_code,
          score,
          reasons,
          similarity_score,
          support_count,
          confidence,
          lift,
          p.pagerank AS pagerank,
          c.rfm_segment AS customer_segment,
          c.rfm_score AS customer_rfm_score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"customer_id": customer_id, "limit": limit},
    )


def run_all_batch_algorithms() -> dict:
    """Entry point para o job agendado (cron/Airflow)."""
    logger.info("graph_algorithms_job_started")

    run_product_similarity()
    run_product_pagerank()
    association_result = run_association_rules()
    segmentation_result = run_customer_segmentation()
    rfm_result = run_customer_rfm()

    logger.info("graph_algorithms_job_complete")
    return {
        "association_rules": association_result,
        "segmentation": segmentation_result,
        "rfm": rfm_result,
    }
