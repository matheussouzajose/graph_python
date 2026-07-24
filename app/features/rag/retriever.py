"""
Retriever híbrido de Graph RAG (via LOCAL).

O padrão aqui é o núcleo do Graph RAG: 1) busca vetorial encontra os nós
mais semanticamente próximos da pergunta, 2) a partir desses nós,
expandimos via Cypher para trazer contexto estrutural (produtos, cliente,
comunidade/segmento, produtos similares) que a busca vetorial sozinha nunca
traria, porque esse contexto não está no texto do embedding, está na
estrutura do grafo.

Busca nos DOIS índices vetoriais (`order_embedding_index` e
`product_embedding_index`), não só em Order: uma pergunta sobre um produto
específico ("produtos parecidos com a camisa azul") deve encontrar o
`Product` diretamente pelo embedding dele — antes disso só era alcançável
indiretamente, via pedidos cujo texto o mencionava, o que nunca trazia
contexto centrado no produto (preço, cores, tamanhos, pagerank, vizinhos
via `SIMILAR_TO`). Os hits das duas buscas são combinados e reordenados por
score antes de expandir contexto, para não gastar expansão Cypher em mais
hits do que o `top_k` pedido.

Quando embeddings ainda nao foram gerados, cai para busca lexical/estrutural
em Neo4j. Embeddings melhoram o recall semantico, mas nao sao obrigatorios
para o `/rag/ask` responder.
"""

from __future__ import annotations

import re

from neo4j.exceptions import Neo4jError
from openai import OpenAI

from app.core.config import settings
from app.core.infrastructure.database.neo4j import run_query
from app.core.logger import logger

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

VECTOR_SEARCH_ORDERS = """
CALL db.index.vector.queryNodes('order_embedding_index', $top_k, $query_embedding)
YIELD node, score
RETURN node.id AS order_id, node.embedding_text AS text, score
ORDER BY score DESC
"""

VECTOR_SEARCH_PRODUCTS = """
CALL db.index.vector.queryNodes('product_embedding_index', $top_k, $query_embedding)
YIELD node, score
RETURN node.id AS product_id, node.embedding_text AS text, score
ORDER BY score DESC
"""

VECTOR_INDEX_NAMES = {"order_embedding_index", "product_embedding_index"}

LEXICAL_SEARCH_ORDERS = """
MATCH (o:Order)
OPTIONAL MATCH (o)-[:PLACED_BY]->(cust:Customer)
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
WITH o, cust, collect(DISTINCT p.name) AS product_names
WHERE any(term IN $terms WHERE
    toLower(toString(coalesce(o.code, ''))) CONTAINS term OR
    toLower(coalesce(o.status, '')) CONTAINS term OR
    toLower(coalesce(o.origin, '')) CONTAINS term OR
    toLower(coalesce(cust.name, '')) CONTAINS term OR
    any(product_name IN product_names WHERE toLower(coalesce(product_name, '')) CONTAINS term)
)
RETURN o.id AS order_id, 0.55 AS score
LIMIT $top_k
"""

LEXICAL_SEARCH_PRODUCTS = """
MATCH (p:Product)
WHERE any(term IN $terms WHERE
    toLower(coalesce(p.name, '')) CONTAINS term OR
    toLower(toString(coalesce(p.code, ''))) CONTAINS term
)
RETURN p.id AS product_id, 0.60 AS score
ORDER BY coalesce(p.pagerank, 0.0) DESC
LIMIT $top_k
"""

STRUCTURAL_FALLBACK_PRODUCTS = """
MATCH (p:Product)
RETURN p.id AS product_id, 0.35 AS score
ORDER BY coalesce(p.pagerank, 0.0) DESC, p.name ASC
LIMIT $top_k
"""

EXPAND_ORDER_CONTEXT = """
MATCH (o:Order {id: $order_id})
OPTIONAL MATCH (o)-[:PLACED_BY]->(cust:Customer)
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
OPTIONAL MATCH (p)-[:SIMILAR_TO]->(similar:Product)
WITH o, cust, collect(DISTINCT p.name) AS products,
     collect(DISTINCT similar.name)[0..3] AS similar_products
RETURN
    o.id AS order_id,
    o.code AS order_code,
    o.status AS status,
    o.total_value AS total_value,
    cust.name AS customer_name,
    cust.community AS customer_community,
    cust.rfm_segment AS customer_segment,
    cust.rfm_score AS customer_rfm_score,
    products,
    similar_products
"""

EXPAND_PRODUCT_CONTEXT = """
MATCH (p:Product {id: $product_id})
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_COLOR]->(color:Color)
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_SIZE]->(size:Size)
OPTIONAL MATCH (p)-[:SIMILAR_TO]->(similar:Product)
WITH p, collect(DISTINCT color.name) AS colors,
     collect(DISTINCT size.name) AS sizes,
     collect(DISTINCT similar.name)[0..3] AS similar_products
RETURN
    p.id AS product_id,
    p.name AS product_name,
    p.code AS product_code,
    p.price AS price,
    p.price_promotional AS price_promotional,
    p.pagerank AS pagerank,
    colors,
    sizes,
    similar_products
"""


def _embed_query(query: str) -> list[float]:
    # `dimensions` explícito para nunca divergir do que `order_embedding_index`
    # foi criado com (ver `embeddings/pipeline.py::create_vector_indexes`) —
    # sem isso, um `OPENAI_EMBEDDING_DIMENSIONS` diferente do default do
    # modelo faria essa query vir com um tamanho de vetor que o index rejeita.
    response = _client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=[query],
        dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def _extract_terms(question: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[\w-]{3,}", question, flags=re.UNICODE)]


def _vector_indexes_ready() -> bool:
    try:
        result = run_query(
            """
            SHOW VECTOR INDEXES
            YIELD name
            WHERE name IN $index_names
            RETURN collect(name) AS names
            """,
            {"index_names": list(VECTOR_INDEX_NAMES)},
        )
    except Neo4jError as e:
        logger.warning("vector_index_check_failed_using_structural_fallback", error=str(e))
        return False

    names = set(result[0]["names"]) if result else set()
    return VECTOR_INDEX_NAMES.issubset(names)


def _vector_hits(question: str, top_k: int) -> tuple[list[dict], list[dict]]:
    if not _vector_indexes_ready():
        logger.info("vector_indexes_missing_using_structural_fallback", question=question)
        return [], []

    try:
        query_embedding = _embed_query(question)
        order_hits = run_query(
            VECTOR_SEARCH_ORDERS,
            {"top_k": top_k, "query_embedding": query_embedding},
        )
        product_hits = run_query(
            VECTOR_SEARCH_PRODUCTS,
            {"top_k": top_k, "query_embedding": query_embedding},
        )
    except Exception as e:
        logger.warning("vector_search_failed_using_structural_fallback", error=str(e))
        return [], []

    logger.info(
        "vector_search_complete",
        question=question,
        order_hits=len(order_hits),
        product_hits=len(product_hits),
    )
    return order_hits, product_hits


def _fallback_hits(question: str, top_k: int) -> tuple[list[dict], list[dict]]:
    terms = _extract_terms(question)
    if not terms:
        return [], run_query(STRUCTURAL_FALLBACK_PRODUCTS, {"top_k": top_k})

    order_hits = run_query(LEXICAL_SEARCH_ORDERS, {"terms": terms, "top_k": top_k})
    product_hits = run_query(LEXICAL_SEARCH_PRODUCTS, {"terms": terms, "top_k": top_k})

    if not order_hits and not product_hits:
        product_hits = run_query(STRUCTURAL_FALLBACK_PRODUCTS, {"top_k": top_k})

    logger.info(
        "structural_fallback_search_complete",
        question=question,
        terms=terms,
        order_hits=len(order_hits),
        product_hits=len(product_hits),
    )
    return order_hits, product_hits


def hybrid_retrieve(question: str, top_k: int = 5) -> list[dict]:
    """
    Retorna uma lista de contextos estruturados (não texto solto), prontos
    para o prompt do LLM montar a resposta com fatos verificáveis. Cada
    contexto carrega `context_type` ("order" ou "product") para
    `chain.py::_format_context` saber qual formatação aplicar.
    """
    order_hits, product_hits = _vector_hits(question, top_k)
    if not order_hits and not product_hits:
        order_hits, product_hits = _fallback_hits(question, top_k)

    enriched_contexts = []
    for hit in order_hits:
        expanded = run_query(EXPAND_ORDER_CONTEXT, {"order_id": hit["order_id"]})
        if expanded:
            context = expanded[0]
            context["context_type"] = "order"
            context["similarity_score"] = hit["score"]
            enriched_contexts.append(context)

    for hit in product_hits:
        expanded = run_query(EXPAND_PRODUCT_CONTEXT, {"product_id": hit["product_id"]})
        if expanded:
            context = expanded[0]
            context["context_type"] = "product"
            context["similarity_score"] = hit["score"]
            enriched_contexts.append(context)

    # Cada índice já veio ordenado por score, mas juntando os dois é preciso
    # reordenar globalmente antes de cortar em top_k — senão um hit fraco de
    # um índice desloca um hit forte do outro.
    enriched_contexts.sort(key=lambda c: c["similarity_score"], reverse=True)
    return enriched_contexts[:top_k]
