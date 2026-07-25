"""
Retriever híbrido de Graph RAG (via LOCAL).

O padrão aqui é o núcleo do Graph RAG: 1) busca vetorial encontra os nós
mais semanticamente próximos da pergunta, 2) a partir desses nós,
expandimos via Cypher para trazer contexto estrutural (produtos, cliente,
comunidade/segmento, produtos similares) que a busca vetorial sozinha nunca
traria, porque esse contexto não está no texto do embedding, está na
estrutura do grafo.

A busca vetorial sobre-busca (`$fetch_k`, um múltiplo de `top_k`) no índice
nativo do Neo4j e só filtra por empresa (`WHERE EXISTS {...BELONGS_TO...}`)
depois do `YIELD`, cortando pra `$top_k` só no final — o índice vetorial do
Neo4j Community não pré-filtra por propriedade arbitrária como `company_id`
antes de calcular os vizinhos mais próximos. Sem esse over-fetch, filtrar só
na expansão de contexto (`_expand`, mais abaixo) descartaria hits de outra
empresa depois de já ter gasto o `top_k` inteiro neles — sem vazar dado (a
expansão também é escopada por empresa e simplesmente não encontra nada pra
um hit de fora), mas devolvendo menos contexto do que deveria pra empresa
certa.

Busca nos TRÊS índices vetoriais (`order_embedding_index`,
`product_embedding_index` e `customer_embedding_index`), não só em Order:
uma pergunta sobre um produto específico ("produtos parecidos com a camisa
azul") deve encontrar o `Product` diretamente pelo embedding dele — antes
disso só era alcançável indiretamente, via pedidos cujo texto o mencionava,
o que nunca trazia contexto centrado no produto (preço, cores, tamanhos,
pagerank, vizinhos via `SIMILAR_TO`). O mesmo valia pra `Customer`: uma
pergunta citando um cliente pelo nome ("explique o comportamento de compra
da cliente X") não tinha nenhum jeito de achar o nó `Customer` — o fallback
léxico casava o termo contra nome de *produto* (`LEXICAL_SEARCH_PRODUCTS`) e
podia devolver um produto com o mesmo nome só por coincidência (ex:
perguntar sobre a cliente "Kelly" batia em produtos como "Vestido Kelly"),
produzindo uma resposta confiante e errada em vez de "sem dados". Os hits
das três buscas são combinados e reordenados por score antes de expandir
contexto, para não gastar expansão Cypher em mais hits do que o `top_k`
pedido.

Quando embeddings ainda nao foram gerados, cai para busca lexical/estrutural
em Neo4j. Embeddings melhoram o recall semantico, mas nao sao obrigatorios
para o `/rag/ask` responder.
"""

from __future__ import annotations

import re
from itertools import zip_longest

from neo4j.exceptions import Neo4jError
from openai import OpenAI

from app.core.config import settings
from app.core.infrastructure.database.neo4j import run_query
from app.core.logger import logger

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

VECTOR_SEARCH_ORDERS = """
CALL db.index.vector.queryNodes('order_embedding_index', $fetch_k, $query_embedding)
YIELD node, score
MATCH (node)-[:BELONGS_TO]->(:Company {id: $company_id})
RETURN node.id AS order_id, node.embedding_text AS text, score
ORDER BY score DESC
LIMIT $top_k
"""

VECTOR_SEARCH_PRODUCTS = """
CALL db.index.vector.queryNodes('product_embedding_index', $fetch_k, $query_embedding)
YIELD node, score
WHERE EXISTS {
    MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
    MATCH (o)-[:CONTAINS]->(node)
}
RETURN node.id AS product_id, node.embedding_text AS text, score
ORDER BY score DESC
LIMIT $top_k
"""

VECTOR_SEARCH_CUSTOMERS = """
CALL db.index.vector.queryNodes('customer_embedding_index', $fetch_k, $query_embedding)
YIELD node, score
WHERE EXISTS {
    MATCH (node)<-[:PLACED_BY]-(:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
}
RETURN node.id AS customer_id, node.embedding_text AS text, score
ORDER BY score DESC
LIMIT $top_k
"""

VECTOR_INDEX_NAMES = {
    "order_embedding_index",
    "product_embedding_index",
    "customer_embedding_index",
}

# Quantos candidatos pedir ao índice vetorial nativo antes de filtrar por
# empresa e cortar em `top_k` (ver docstring do módulo) — alto o bastante pra
# sobrar `top_k` resultados da empresa certa mesmo com outras empresas
# competindo pelos vizinhos mais próximos, sem pedir um `fetch_k` ilimitado.
_VECTOR_FETCH_MULTIPLIER = 8
_VECTOR_FETCH_CAP = 200

LEXICAL_SEARCH_ORDERS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
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

# Mesmo padrão de dedup + ranking por especificidade de `LEXICAL_SEARCH_CUSTOMERS`
# (ver comentário lá) — sem `DISTINCT p`, um produto vendido em N pedidos
# aparecia N vezes só nesta busca, e ordenar só por `pagerank` (sem relação
# com o quão bem o termo bate) deixava um produto popular, mas só
# parcialmente relacionado à pergunta, aparecer antes do produto que o
# usuário realmente perguntou.
LEXICAL_SEARCH_PRODUCTS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:CONTAINS]->(p:Product)
WITH DISTINCT p
WITH p, [term IN $terms WHERE
    toLower(coalesce(p.name, '')) CONTAINS term OR
    toLower(toString(coalesce(p.code, ''))) CONTAINS term
] AS matched_terms
WHERE size(matched_terms) > 0
RETURN p.id AS product_id, 0.5 + (0.05 * size(matched_terms)) AS score
ORDER BY size(matched_terms) DESC, coalesce(p.pagerank, 0.0) DESC
LIMIT $top_k
"""

# Nome/documento/email/cidade/estado — cobre tanto "cliente Fulano de Tal"
# quanto "clientes em SP" quando essa pergunta acaba caindo em LOCAL em vez
# de GLOBAL (o texto do cliente carrega cidade/estado, ver
# `embeddings/text_builder.py::build_customer_text`).
#
# `WITH DISTINCT c` antes do filtro é obrigatório: sem ele, cada pedido do
# cliente gera uma linha duplicada dele mesmo, e um cliente com muitos
# pedidos podia sozinho preencher o `top_k` inteiro com N cópias de si mesmo
# (confirmado ao vivo: um cliente com 11 pedidos aparecia 11 vezes). Ranquear
# por `size(matched_terms)` (quantos termos da pergunta bateram) antes de
# `rfm_score` também é obrigatório — sobrenomes comuns em português (ex:
# "Alves", "Soares") batem por coincidência em vários clientes não
# relacionados, e ordenar só por `rfm_score` (sem relação com relevância)
# deixava esses falsos positivos, quando tinham `rfm_score` mais alto,
# expulsarem o cliente certo do `top_k` mesmo ele batendo o nome inteiro.
LEXICAL_SEARCH_CUSTOMERS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:PLACED_BY]->(c:Customer)
WITH DISTINCT c
WITH c, [term IN $terms WHERE
    toLower(coalesce(c.name, '')) CONTAINS term OR
    toLower(coalesce(c.document, '')) CONTAINS term OR
    toLower(coalesce(c.email, '')) CONTAINS term OR
    toLower(coalesce(c.city_name, '')) CONTAINS term OR
    toLower(coalesce(c.state_initials, '')) CONTAINS term
] AS matched_terms
WHERE size(matched_terms) > 0
RETURN c.id AS customer_id, 0.5 + (0.05 * size(matched_terms)) AS score
ORDER BY size(matched_terms) DESC, coalesce(c.rfm_score, 0) DESC
LIMIT $top_k
"""

STRUCTURAL_FALLBACK_PRODUCTS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:CONTAINS]->(p:Product)
WITH DISTINCT p
RETURN p.id AS product_id, 0.35 AS score
ORDER BY coalesce(p.pagerank, 0.0) DESC, p.name ASC
LIMIT $top_k
"""

EXPAND_ORDER_CONTEXT = """
MATCH (o:Order {id: $order_id})-[:BELONGS_TO]->(:Company {id: $company_id})
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
WHERE EXISTS {
    MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
    MATCH (o)-[:CONTAINS]->(p)
}
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_COLOR]->(color:Color)
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_SIZE]->(size:Size)
OPTIONAL MATCH (p)<-[:CONTAINS]-(o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (o)-[:PLACED_BY]->(buyer:Customer)
WITH p, collect(DISTINCT color.name) AS colors,
     collect(DISTINCT size.name) AS sizes,
     collect(DISTINCT buyer.name)[0..5] AS buyers,
     collect(DISTINCT o.code)[0..5] AS recent_order_codes
CALL {
    WITH p
    MATCH (p)-[s:SIMILAR_TO]->(similar:Product)
    RETURN collect(
        {name: similar.name, code: similar.code, score: s.score}
    )[0..3] AS similar_products
}
CALL {
    WITH p
    MATCH (p)-[b:BOUGHT_WITH]->(assoc:Product)
    RETURN collect({
        name: assoc.name, code: assoc.code,
        support_count: b.support_count, confidence: b.confidence, lift: b.lift
    })[0..3] AS bought_with_products
}
RETURN
    p.id AS product_id,
    p.name AS product_name,
    p.code AS product_code,
    p.price AS price,
    p.price_promotional AS price_promotional,
    p.pagerank AS pagerank,
    colors,
    sizes,
    similar_products,
    bought_with_products,
    buyers,
    recent_order_codes
"""

EXPAND_CUSTOMER_CONTEXT = """
MATCH (c:Customer {id: $customer_id})<-[:PLACED_BY]-(:Order)
      -[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (c)<-[:PLACED_BY]-(o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
WITH c, collect(DISTINCT p)[0..8] AS owned_products
CALL {
    WITH owned_products
    UNWIND owned_products AS op
    MATCH (op)-[b:BOUGHT_WITH]->(rec:Product)
    WHERE NOT rec IN owned_products
    RETURN collect(DISTINCT {
        name: rec.name, code: rec.code, based_on: op.name,
        confidence: b.confidence, lift: b.lift
    })[0..5] AS recommended_products
}
RETURN
    c.id AS customer_id,
    c.name AS customer_name,
    c.rfm_segment AS rfm_segment,
    c.rfm_score AS rfm_score,
    c.rfm_frequency AS rfm_frequency,
    c.rfm_monetary AS rfm_monetary,
    c.rfm_recency_days AS rfm_recency_days,
    c.city_name AS city_name,
    c.state_initials AS state_initials,
    c.community AS community,
    [x IN owned_products | x.name] AS products,
    recommended_products
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


# Palavras funcionais em português que aparecem em quase toda pergunta
# (sobretudo em perguntas de "por que") e coincidem por acaso como substring
# de nome/email/cidade de clientes não relacionados (confirmado ao vivo:
# "por"/"que" batiam em 57 clientes via e-mail/cidade só por coincidência de
# substring) — sem filtrar isso, a busca lexical de fallback fica poluída de
# falsos positivos que competem pelo `top_k` com o termo que importa de
# verdade (ex: o nome do cliente perguntado).
_STOPWORDS = {
    "por",
    "que",
    "para",
    "com",
    "sem",
    "uma",
    "dos",
    "das",
    "nos",
    "nas",
    "tem",
    "ter",
    "foi",
    "sao",
    "são",
    "está",
    "esta",
    "isso",
    "essa",
    "esse",
    "como",
    "quando",
    "onde",
    "qual",
    "quais",
}


def _extract_terms(question: str) -> list[str]:
    terms = [term.lower() for term in re.findall(r"[\w-]{3,}", question, flags=re.UNICODE)]
    return [term for term in terms if term not in _STOPWORDS]


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


def _vector_hits(
    question: str, top_k: int, company_id: str
) -> tuple[list[dict], list[dict], list[dict]]:
    if not _vector_indexes_ready():
        logger.info("vector_indexes_missing_using_structural_fallback", question=question)
        return [], [], []

    fetch_k = min(top_k * _VECTOR_FETCH_MULTIPLIER, _VECTOR_FETCH_CAP)
    try:
        query_embedding = _embed_query(question)
        params = {
            "top_k": top_k,
            "fetch_k": fetch_k,
            "query_embedding": query_embedding,
            "company_id": company_id,
        }
        order_hits = run_query(VECTOR_SEARCH_ORDERS, params)
        product_hits = run_query(VECTOR_SEARCH_PRODUCTS, params)
        customer_hits = run_query(VECTOR_SEARCH_CUSTOMERS, params)
    except Exception as e:
        logger.warning("vector_search_failed_using_structural_fallback", error=str(e))
        return [], [], []

    logger.info(
        "vector_search_complete",
        question=question,
        order_hits=len(order_hits),
        product_hits=len(product_hits),
        customer_hits=len(customer_hits),
    )
    return order_hits, product_hits, customer_hits


def _fallback_hits(
    question: str, top_k: int, company_id: str
) -> tuple[list[dict], list[dict], list[dict]]:
    terms = _extract_terms(question)
    if not terms:
        return (
            [],
            run_query(STRUCTURAL_FALLBACK_PRODUCTS, {"company_id": company_id, "top_k": top_k}),
            [],
        )

    params = {"company_id": company_id, "terms": terms, "top_k": top_k}
    order_hits = run_query(LEXICAL_SEARCH_ORDERS, params)
    product_hits = run_query(LEXICAL_SEARCH_PRODUCTS, params)
    customer_hits = run_query(LEXICAL_SEARCH_CUSTOMERS, params)

    if not order_hits and not product_hits and not customer_hits:
        product_hits = run_query(
            STRUCTURAL_FALLBACK_PRODUCTS, {"company_id": company_id, "top_k": top_k}
        )

    logger.info(
        "structural_fallback_search_complete",
        question=question,
        terms=terms,
        order_hits=len(order_hits),
        product_hits=len(product_hits),
        customer_hits=len(customer_hits),
    )
    return order_hits, product_hits, customer_hits


def _expand(
    hits: list[dict], query: str, id_key: str, context_type: str, company_id: str
) -> list[dict]:
    results = []
    for hit in hits:
        expanded = run_query(query, {"company_id": company_id, id_key: hit[id_key]})
        if expanded:
            context = expanded[0]
            context["context_type"] = context_type
            context["similarity_score"] = hit["score"]
            results.append(context)
    return results


def hybrid_retrieve(question: str, top_k: int = 5, company_id: str | None = None) -> list[dict]:
    """
    Retorna uma lista de contextos estruturados (não texto solto), prontos
    para o prompt do LLM montar a resposta com fatos verificáveis. Cada
    contexto carrega `context_type` ("order", "product" ou "customer") para
    `chain.py::_format_context` saber qual formatação aplicar.
    """
    if company_id is None:
        return []

    order_hits, product_hits, customer_hits = _vector_hits(question, top_k, company_id)
    used_fallback = False
    if not order_hits and not product_hits and not customer_hits:
        order_hits, product_hits, customer_hits = _fallback_hits(question, top_k, company_id)
        used_fallback = True

    order_contexts = _expand(order_hits, EXPAND_ORDER_CONTEXT, "order_id", "order", company_id)
    product_contexts = _expand(
        product_hits, EXPAND_PRODUCT_CONTEXT, "product_id", "product", company_id
    )
    customer_contexts = _expand(
        customer_hits, EXPAND_CUSTOMER_CONTEXT, "customer_id", "customer", company_id
    )

    if used_fallback:
        # No fallback léxico, `score` é só um valor fixo por categoria
        # (0.55/0.60/...) pra desempate de exibição — não é uma medida de
        # relevância comparável entre tipos como é a similaridade de cosseno
        # da busca vetorial. Ordenar globalmente por esse score faz a
        # categoria com o valor mais alto engolir o `top_k` inteiro sempre
        # que ela sozinha já tem `top_k` hits, mesmo com as outras categorias
        # tendo hits igualmente (ou mais) relevantes — foi exatamente isso
        # que causava a alucinação de cliente: perguntar por uma cliente pelo
        # nome batia tanto em `Customer.name` quanto, por coincidência, em
        # `Product.name`, e como produto tinha o score fixo mais alto, os
        # hits de cliente de verdade nunca apareciam no contexto. Intercalar
        # por categoria garante que todo tipo com hit real entre no top_k.
        interleaved = [
            context
            for group in zip_longest(customer_contexts, product_contexts, order_contexts)
            for context in group
            if context is not None
        ]
        return interleaved[:top_k]

    enriched_contexts = order_contexts + product_contexts + customer_contexts
    # Vindo da busca vetorial, o score é cosseno real e comparável entre os
    # três índices (mesmo espaço de embedding) — aí sim faz sentido ordenar
    # globalmente antes de cortar em top_k.
    enriched_contexts.sort(key=lambda c: c["similarity_score"], reverse=True)
    return enriched_contexts[:top_k]
