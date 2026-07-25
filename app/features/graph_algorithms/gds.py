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

Todas as projeções GDS (`_project_product_graph`/`_project_customer_graph`)
são escopadas por empresa via `gds.graph.project.cypher` (projeção via query,
não a nativa por label) — a nativa (`gds.graph.project(name, labels, rels)`)
não tem como filtrar por uma propriedade arbitrária como `company_id`, só por
label. Sem esse filtro, `pagerank`/`community`/`SIMILAR_TO` ficariam
contaminados por estrutura de compra de outras empresas mesmo que os
endpoints de leitura já filtrem qual *resultado* aparece pra cada uma —
testado ao vivo (`gds.graph.project.cypher` funciona nesta versão do GDS,
2.13.10). O nome da projeção carrega o `company_id`
(`produtos-coocorrencia-<company_id>`) pra uma empresa nunca sobrescrever a
projeção nomeada de outra. `relationship_query` some UNION ALL nas duas
direções porque a projeção via Cypher não tem um flag `orientation:
'UNDIRECTED'` pronto como a nativa tinha — emitir os dois sentidos é o jeito
de simular undirected (confirmado ao vivo: sem isso, metade dos vizinhos
nunca aparece pro FastRP/KNN/Leiden).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.infrastructure.database.neo4j import run_query
from app.core.logger import logger

PRODUCT_GRAPH_PREFIX = "produtos-coocorrencia"
CUSTOMER_GRAPH_PREFIX = "clientes-produtos"

# Modularity mínima aceitável para persistir o resultado do Leiden.
# Abaixo disso, as comunidades não têm estrutura real e não deveriam
# ser gravadas (indicativo de dado insuficiente ou muito ruidoso).
MIN_MODULARITY_THRESHOLD = 0.1

DEFAULT_ASSOCIATION_MIN_SUPPORT_COUNT = 2
DEFAULT_ASSOCIATION_MIN_CONFIDENCE = 0.05


def product_graph_name(company_id: str) -> str:
    return f"{PRODUCT_GRAPH_PREFIX}-{company_id}"


def customer_graph_name(company_id: str) -> str:
    return f"{CUSTOMER_GRAPH_PREFIX}-{company_id}"


def _drop_graph_if_exists(graph_name: str) -> None:
    run_query("CALL gds.graph.drop($name, false)", {"name": graph_name})


def _record_run(name: str, company_id: str, **details: object) -> None:
    """Marca quando cada algoritmo rodou por último, num nó `AlgorithmRun`
    dedicado (não uma propriedade em cada nó tocado — mais barato de
    escrever e dá um único lugar pra consultar "quando isso rodou por
    último"), agora um por empresa (`name` + `company_id` juntos formam a
    chave) — senão o "última execução" de uma empresa aparecia misturado
    com o de outra. Como o schema exposto ao `GraphCypherQAChain` (via
    `rag/cypher_qa.py`'s `enhanced_schema=True`) é lido diretamente do banco,
    o LLM da via GLOBAL já consegue responder "quando a segmentação rodou
    pela última vez" sem nenhum código novo do lado do RAG — só precisa que
    esse nó exista."""
    run_query(
        "MERGE (run:AlgorithmRun {name: $name, company_id: $company_id}) "
        "SET run.computed_at = datetime(), run += $details",
        {"name": name, "company_id": company_id, "details": details},
    )


def _product_embedding_count(company_id: str) -> int:
    result = run_query(
        """
        MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        MATCH (o)-[:CONTAINS]->(p:Product)
        WHERE p.text_embedding IS NOT NULL
        RETURN count(DISTINCT p) AS count
        """,
        {"company_id": company_id},
    )
    return int(result[0]["count"]) if result else 0


# Ambas as projeções usam a API de "Cypher Aggregation" do GDS
# (`gds.graph.project(...)` como *função agregadora*, chamada uma vez por
# linha dentro de um `WITH`) — não o procedimento `gds.graph.project.cypher`.
# Motivo: só a função agregadora aceita `undirectedRelationshipTypes` de
# verdade (testado ao vivo nesta versão do GDS, 2.13.10); o procedimento
# `.cypher` sempre projeta como `DIRECTED`, mesmo emitindo as duas direções
# manualmente via `UNION ALL` — o Leiden (`run_customer_segmentation`) rejeita
# um grafo assim ("works only with undirected graphs").
_PRODUCT_PROJECT_QUERY = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:CONTAINS]->(p:Product)
WITH o, p, coalesce(p.text_embedding, $zero_embedding) AS product_embedding
WITH gds.graph.project(
  $graph_name, o, p,
  {
    sourceNodeLabels: ['Order'],
    targetNodeLabels: ['Product'],
    sourceNodeProperties: {text_embedding: $zero_embedding},
    targetNodeProperties: {text_embedding: product_embedding},
    relationshipType: 'CONTAINS'
  },
  {undirectedRelationshipTypes: ['*']}
) AS g
RETURN g.graphName AS graphName, g.nodeCount AS nodeCount, g.relationshipCount AS relationshipCount
"""

_CUSTOMER_PROJECT_QUERY = """
CALL {
  MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
  MATCH (o)-[:PLACED_BY]->(c:Customer)
  RETURN o AS source, c AS target,
         'Order' AS source_labels, 'Customer' AS target_labels, 'PLACED_BY' AS rel_type
  UNION
  MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
  MATCH (o)-[:CONTAINS]->(p:Product)
  RETURN o AS source, p AS target,
         'Order' AS source_labels, 'Product' AS target_labels, 'CONTAINS' AS rel_type
}
WITH gds.graph.project(
  $graph_name, source, target,
  {
    sourceNodeLabels: [source_labels],
    targetNodeLabels: [target_labels],
    relationshipType: rel_type
  },
  {undirectedRelationshipTypes: ['*']}
) AS g
RETURN g.graphName AS graphName, g.nodeCount AS nodeCount, g.relationshipCount AS relationshipCount
"""


def _project_product_graph(company_id: str) -> str:
    """Projeta `text_embedding` junto com a topologia, com um vetor de zeros
    como valor pra `Order` (que nunca tem embedding de produto) e como
    fallback pra `Product` que ainda não passou por `embeddings/pipeline.py`
    — sem isso o KNN falharia exigindo a propriedade em todo nó do grafo
    projetado. Um nó sem embedding real só perde o sinal semântico nessa
    rodada (fica só com o estrutural do FastRP), não quebra o job."""
    graph_name = product_graph_name(company_id)
    _drop_graph_if_exists(graph_name)
    zero_embedding = [0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS
    run_query(
        _PRODUCT_PROJECT_QUERY,
        {"graph_name": graph_name, "company_id": company_id, "zero_embedding": zero_embedding},
    )
    logger.info("graph_projected", graph=graph_name)
    return graph_name


def _project_customer_graph(company_id: str) -> str:
    graph_name = customer_graph_name(company_id)
    _drop_graph_if_exists(graph_name)
    run_query(
        _CUSTOMER_PROJECT_QUERY,
        {"graph_name": graph_name, "company_id": company_id},
    )
    logger.info("graph_projected", graph=graph_name)
    return graph_name


def run_product_similarity(company_id: str) -> None:
    """FastRP (embedding estrutural) + KNN aproximado — escala para catálogos
    grandes. KNN combina `structuralEmbedding` (FastRP, sinal de compra) com
    `text_embedding` (OpenAI, sinal semântico) — cada propriedade entra com
    sua própria similaridade de cosseno e o GDS normaliza e combina as duas
    num único score por par, em vez de escolher uma ou outra."""
    graph_name = _project_product_graph(company_id)

    run_query(
        """
        CALL gds.fastRP.mutate($graph_name, {
          embeddingDimension: 128,
          mutateProperty: 'structuralEmbedding',
          randomSeed: 42
        })
        """,
        {"graph_name": graph_name},
    )
    logger.info("fastrp_computed", graph=graph_name)

    node_properties = "[{structuralEmbedding: 'COSINE'}]"
    embedding_count = _product_embedding_count(company_id)
    if embedding_count > 0:
        node_properties = "[{structuralEmbedding: 'COSINE'}, {text_embedding: 'COSINE'}]"

    result = run_query(
        f"""
        CALL gds.knn.mutate($graph_name, {{
          nodeProperties: {node_properties},
          mutateRelationshipType: 'SIMILAR_TO',
          mutateProperty: 'score',
          topK: 5,
          sampleRate: 1.0
        }})
        YIELD nodesCompared, relationshipsWritten
        """,
        {"graph_name": graph_name},
    )
    logger.info(
        "knn_computed",
        graph=graph_name,
        result=result,
        embeddings_used=embedding_count > 0,
    )

    # Persiste no banco principal só depois do cálculo confirmado em memória.
    run_query(
        "CALL gds.graph.relationship.write($graph_name, 'SIMILAR_TO', 'score')",
        {"graph_name": graph_name},
    )
    _record_run("product_similarity", company_id)
    logger.info("product_similarity_persisted")


def run_product_pagerank(company_id: str) -> None:
    """PageRank — importância estrutural do produto na rede de compras
    *desta empresa* (a projeção em `_project_product_graph` já é escopada)."""
    graph_name = product_graph_name(company_id)
    run_query(
        "CALL gds.pageRank.write($graph_name, {writeProperty: 'pagerank'})",
        {"graph_name": graph_name},
    )
    _record_run("product_pagerank", company_id)
    logger.info("pagerank_persisted", graph=graph_name)


def run_customer_segmentation(company_id: str) -> dict:
    """Leiden para segmentação de clientes — só persiste se modularity for aceitável."""
    graph_name = _project_customer_graph(company_id)

    result = run_query(
        "CALL gds.leiden.mutate($graph_name, {mutateProperty: 'community'}) "
        "YIELD communityCount, modularity",
        {"graph_name": graph_name},
    )[0]

    modularity = result["modularity"]
    logger.info(
        "leiden_computed",
        graph=graph_name,
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

    run_query(
        "CALL gds.graph.nodeProperties.write($graph_name, ['community'])",
        {"graph_name": graph_name},
    )
    _record_run(
        "customer_segmentation",
        company_id,
        community_count=result["communityCount"],
        modularity=modularity,
    )
    logger.info("customer_segmentation_persisted")
    return {"persisted": True, **result}


def run_customer_rfm(company_id: str) -> dict:
    """Calcula RFM explicavel por cliente e grava no proprio no `Customer`,
    escopado aos pedidos desta empresa.

    Os thresholds sao absolutos de partida, adequados enquanto o volume ainda
    e pequeno. Quando houver historico maior, esta funcao pode evoluir para
    pontuacao por percentis sem mudar o contrato consumido pelas APIs/RAG.

    De quebra, tambem denormaliza `city_name`/`state_initials` no proprio
    `Customer`, a partir do endereco de entrega do pedido mais recente
    (`ORDER BY o.created_at DESC` antes do `WITH` agregador + `head(collect(o))`
    pega esse pedido sem precisar de uma segunda travessia do grafo). Motivo:
    `Customer` nao tem relacao direta com `City`/`State` — so da pra chegar la
    via `Customer<-[:PLACED_BY]-Order-[:SHIPPED_TO]->Address-[:LOCATED_IN]->City`,
    um traversal de 4 hops com a primeira relacao invertida que o LLM do
    Graph RAG (via GLOBAL, `cypher_qa.py`) consistentemente erra ao gerar
    Cypher para perguntas de filtro por um estado especifico (ex: "quantos
    clientes existem em SP") — confirmado nos logs como erro de sintaxe
    (`[:PLACED_BY|:PLACED_BY*0..]`, que nao existe). Com o dado aqui, essas
    perguntas viram um filtro de 1 hop, trivial de gerar certo.
    """
    result = run_query(
        """
        MATCH (c:Customer)<-[:PLACED_BY]-(o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        WITH c, o
        ORDER BY o.created_at DESC
        WITH
          c,
          count(o) AS frequency,
          sum(coalesce(o.total_value, 0.0)) AS monetary,
          max(o.created_at) AS last_order_at,
          head(collect(o)) AS latest_order
        OPTIONAL MATCH
          (latest_order)-[:SHIPPED_TO]->(:Address)-[:LOCATED_IN]->(city:City)-[:IN_STATE]->(state:State)
        WITH
          c,
          frequency,
          monetary,
          last_order_at,
          city.name AS city_name,
          state.initials AS state_initials,
          CASE
            WHEN last_order_at IS NULL THEN 9999
            ELSE duration.inDays(date(last_order_at), date()).days
          END AS recency_days
        WITH
          c,
          frequency,
          monetary,
          last_order_at,
          city_name,
          state_initials,
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
          city_name,
          state_initials,
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
          c.city_name = city_name,
          c.state_initials = state_initials,
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
        """,
        {"company_id": company_id},
    )
    payload = result[0] if result else {"customers_scored": 0}
    _record_run("customer_rfm", company_id, **payload)
    logger.info("customer_rfm_persisted", result=payload)
    return payload


def run_association_rules(
    company_id: str,
    min_support_count: int = DEFAULT_ASSOCIATION_MIN_SUPPORT_COUNT,
    min_confidence: float = DEFAULT_ASSOCIATION_MIN_CONFIDENCE,
) -> dict:
    """Calcula regras direcionais produto -> produto via pedidos
    compartilhados, escopado aos pedidos desta empresa (senão `BOUGHT_WITH`
    poderia ligar produtos de empresas diferentes que nunca foram comprados
    juntos de verdade).

    `a_orders`/`b_orders` (quantos pedidos contêm o produto, usado pra
    normalizar confidence/lift) **não** repetem o filtro
    `-[:BELONGS_TO]->(:Company {id: $company_id})` — não precisam: como
    `graph_normalizer.py::_scoped` já compõe `Product.id` como
    `"{company_id}:{raw_id}"`, um `Product` é um nó exclusivo de uma empresa
    só, então qualquer `Order` conectado a ele via `CONTAINS` já é
    necessariamente um pedido dessa mesma empresa. Repetir o filtro aqui
    seria redundante e caro: testado ao vivo, com pedidos de até ~97
    produtos o self-join gera ~517 mil pares candidatos, e repetir o hop
    `BELONGS_TO` (via `COUNT {}` ou `MATCH`) nessa escala estourava tanto o
    timeout quanto o limite de memória de transação do Neo4j
    (`dbms.transaction.timeout`/`dbms.memory.transaction.total.max`, ver
    `docker-compose.yml`). Sem esse hop redundante, a query volta ao mesmo
    custo de antes de existir multi-tenant. `pair_orders >= $min_support_count`
    filtra antes de calcular `a_orders`/`b_orders` pelo mesmo motivo: a
    maioria dos pares só aparece junto 1 vez e nem chega a precisar dessas
    duas contagens."""
    result = run_query(
        """
        MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        WHERE EXISTS { (o)-[:CONTAINS]->(:Product) }
        WITH count(o) AS total_orders
        MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        MATCH (a:Product)<-[:CONTAINS]-(o)-[:CONTAINS]->(b:Product)
        WHERE a.id <> b.id
        WITH total_orders, a, b, count(DISTINCT o) AS pair_orders
        WHERE pair_orders >= $min_support_count
        WITH
          total_orders,
          a,
          b,
          pair_orders,
          COUNT { (a)<-[:CONTAINS]-(:Order) } AS a_orders,
          COUNT { (b)<-[:CONTAINS]-(:Order) } AS b_orders
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
        WHERE confidence >= $min_confidence
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
            "company_id": company_id,
            "min_support_count": min_support_count,
            "min_confidence": min_confidence,
        },
    )
    payload = result[0] if result else {"rules_written": 0}
    payload["min_support_count"] = min_support_count
    payload["min_confidence"] = min_confidence
    _record_run("association_rules", company_id, **payload)
    logger.info("association_rules_persisted", result=payload)
    return payload


def run_personalized_pagerank(
    product_ids: list[str], limit: int = 10, company_id: str | None = None
) -> list[dict]:
    """
    PageRank personalizado — usado em tempo real (via API/retriever), não em
    batch. Recebe os `Product.id` de domínio (ex: produtos que o cliente já
    comprou), resolve para os nós internos do grafo já projetado e retorna
    ranking contextual, não o ranking global.

    Depende da projeção nomeada por empresa já existir (`/graph-algorithms/run`
    ou `/graph-algorithms/rfm/run`... na verdade quem cria essa projeção é
    `run_product_similarity`/`run_product_pagerank`, via `/graph-algorithms/run`
    ou chamadas avulsas) — sem `company_id` não tem como saber qual grafo
    nomeado consultar, então retorna vazio em vez de adivinhar.
    """
    if not company_id:
        return []

    graph_name = product_graph_name(company_id)
    return run_query(
        """
        MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        MATCH (o)-[:CONTAINS]->(p:Product)
        WHERE p.id IN $product_ids
        WITH collect(DISTINCT p) AS sourceNodes
        CALL gds.pageRank.stream($graph_name, {sourceNodes: sourceNodes})
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE node:Product
        RETURN node.id AS product_id, node.name AS product_name, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {
            "product_ids": product_ids,
            "limit": limit,
            "company_id": company_id,
            "graph_name": graph_name,
        },
    )


def recommend_by_product(
    product_id: str, limit: int = 10, company_id: str | None = None
) -> list[dict]:
    return run_query(
        """
        MATCH (seed:Product {id: $product_id})
        WHERE $company_id IS NULL OR EXISTS {
          MATCH (seed_order:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
          MATCH (seed_order)-[:CONTAINS]->(seed)
        }
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
        WHERE $company_id IS NULL OR EXISTS {
          MATCH (candidate_order:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
          MATCH (candidate_order)-[:CONTAINS]->(p)
        }
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
        {"product_id": product_id, "limit": limit, "company_id": company_id},
    )


def recommend_by_customer(
    customer_id: str, limit: int = 10, company_id: str | None = None
) -> list[dict]:
    return run_query(
        """
        MATCH (c:Customer {id: $customer_id})
        WHERE $company_id IS NULL OR EXISTS {
          MATCH (c)<-[:PLACED_BY]-(:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
        }
        OPTIONAL MATCH (c)<-[:PLACED_BY]-(owned_order:Order)
          -[:BELONGS_TO]->(:Company {id: $company_id})
        OPTIONAL MATCH (owned_order)-[:CONTAINS]->(owned:Product)
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
          AND ($company_id IS NULL OR EXISTS {
            MATCH (candidate_order:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
            MATCH (candidate_order)-[:CONTAINS]->(p)
          })
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
        {"customer_id": customer_id, "limit": limit, "company_id": company_id},
    )


def run_all_batch_algorithms(company_id: str) -> dict:
    """Entry point para o job agendado (cron/Airflow), escopado a uma empresa
    por vez — quem dispara pra todas as empresas é o chamador (ex: um cron
    futuro iterando `GET /companies`, ou hoje o gatilho manual por usuário
    logado em `graph_algorithms/router.py`)."""
    logger.info("graph_algorithms_job_started", company_id=company_id)

    run_product_similarity(company_id)
    run_product_pagerank(company_id)
    association_result = run_association_rules(company_id)
    segmentation_result = run_customer_segmentation(company_id)
    rfm_result = run_customer_rfm(company_id)

    logger.info("graph_algorithms_job_complete", company_id=company_id)
    return {
        "association_rules": association_result,
        "segmentation": segmentation_result,
        "rfm": rfm_result,
    }
