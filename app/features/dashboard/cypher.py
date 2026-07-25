"""Queries de leitura sobre o grafo Order/Product/Customer já projetado por
`order/graph_sync.py` e enriquecido por `graph_algorithms/gds.py`
(`pagerank`, `SIMILAR_TO`, `BOUGHT_WITH`, `rfm_*`) e `embeddings/pipeline.py`.

Nenhuma query aqui escreve no grafo — este módulo é só leitura agregada para
o dashboard, nunca reusado pelos jobs em batch (que têm suas próprias queries
em `graph_algorithms/gds.py` e `order/graph_cypher.py`).
"""

OVERVIEW_TOTALS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
WITH count(o) AS total_orders,
     sum(coalesce(o.total_value, 0.0)) AS total_revenue,
     avg(o.total_value) AS average_ticket
OPTIONAL MATCH (company_order:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (company_order)-[:PLACED_BY]->(c:Customer)
WITH total_orders, total_revenue, average_ticket, count(DISTINCT c) AS unique_customers
OPTIONAL MATCH (product_order:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (product_order)-[:CONTAINS]->(p:Product)
RETURN
    total_orders,
    total_revenue,
    coalesce(average_ticket, 0.0) AS average_ticket,
    unique_customers,
    count(DISTINCT p) AS products_sold
"""

ORDERS_BY_STATUS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
WHERE o.status IS NOT NULL
RETURN o.status AS status, count(o) AS count
ORDER BY count DESC
"""

LAST_ALGORITHM_RUN = """
MATCH (r:AlgorithmRun {company_id: $company_id})
RETURN max(r.computed_at) AS computed_at
"""

ALGORITHM_RUNS = """
MATCH (r:AlgorithmRun {company_id: $company_id})
RETURN r.name AS name, r.computed_at AS computed_at
ORDER BY r.computed_at DESC
"""

TOP_SELLING_PRODUCTS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[c:CONTAINS]->(p:Product)
WITH p, sum(coalesce(c.requested, 0)) AS quantity_sold
WHERE quantity_sold > 0
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, quantity_sold
ORDER BY quantity_sold DESC
LIMIT $limit
"""

TOP_REVENUE_PRODUCTS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[c:CONTAINS]->(p:Product)
WITH p, sum(coalesce(c.requested, 0) * coalesce(p.price_promotional, p.price, 0.0)) AS revenue
WHERE revenue > 0
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, revenue
ORDER BY revenue DESC
LIMIT $limit
"""

TOP_PAGERANK_PRODUCTS = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:CONTAINS]->(p:Product)
WHERE p.pagerank IS NOT NULL
WITH DISTINCT p
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, p.pagerank AS pagerank
ORDER BY p.pagerank DESC
LIMIT $limit
"""

# `BOUGHT_WITH` já é uma estatística pré-computada por par de produtos (uma
# vez só, pelo job de association rules em `graph_algorithms/gds.py`), não
# por pedido. O `MATCH (o)-[:CONTAINS]->(a)` serve só para confirmar que `a`
# pertence à empresa — mas por ser um `MATCH` (não um filtro de existência),
# ele gera uma linha por PEDIDO que contém `a`, multiplicando cada par
# `BOUGHT_WITH` pelo número de pedidos em que `a` aparece (confirmado ao
# vivo: produto em 2 pedidos da empresa -> cada par duplicado 2x). `WHERE
# EXISTS {...}` faz a mesma checagem de posse sem fan-out — mesmo padrão já
# usado em `rag/retriever.py::VECTOR_SEARCH_PRODUCTS`.
BOUGHT_TOGETHER_ALL = """
MATCH (a:Product)-[b:BOUGHT_WITH]->(c:Product)
WHERE EXISTS {
    MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
    MATCH (o)-[:CONTAINS]->(a)
}
RETURN
    a.id AS product_id, a.name AS product_name, a.code AS product_code,
    c.id AS related_product_id, c.name AS related_product_name, c.code AS related_product_code,
    b.support_count AS support_count, b.confidence AS confidence, b.lift AS lift
ORDER BY b.lift DESC
LIMIT $limit
"""

BOUGHT_TOGETHER_FOR_PRODUCT = """
MATCH (a:Product {id: $product_id})-[b:BOUGHT_WITH]->(c:Product)
WHERE EXISTS {
    MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
    MATCH (o)-[:CONTAINS]->(a)
}
RETURN
    a.id AS product_id, a.name AS product_name, a.code AS product_code,
    c.id AS related_product_id, c.name AS related_product_name, c.code AS related_product_code,
    b.support_count AS support_count, b.confidence AS confidence, b.lift AS lift
ORDER BY b.lift DESC
LIMIT $limit
"""

RFM_SEGMENT_SUMMARY = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:PLACED_BY]->(c:Customer)
WHERE c.rfm_segment IS NOT NULL
WITH DISTINCT c
RETURN
    c.rfm_segment AS segment,
    count(c) AS customer_count,
    avg(c.rfm_recency_days) AS avg_recency_days,
    avg(c.rfm_frequency) AS avg_frequency,
    avg(c.rfm_monetary) AS avg_monetary
ORDER BY customer_count DESC
"""

# `$segment` pode ser `None` — nesse caso o filtro é ignorado e retorna todo
# cliente com RFM já calculado (não-calculado não interessa ao dashboard).
CUSTOMERS_LIST = """
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
MATCH (o)-[:PLACED_BY]->(c:Customer)
WHERE c.rfm_segment IS NOT NULL
  AND ($segment IS NULL OR c.rfm_segment = $segment)
WITH DISTINCT c
RETURN
    c.id AS customer_id,
    c.name AS name,
    c.email AS email,
    c.document AS document,
    c.rfm_segment AS rfm_segment,
    c.rfm_score AS rfm_score,
    c.rfm_recency_days AS rfm_recency_days,
    c.rfm_frequency AS rfm_frequency,
    c.rfm_monetary AS rfm_monetary,
    c.last_order_at AS last_order_at,
    c.city_name AS city_name,
    c.state_initials AS state_initials
ORDER BY c.rfm_score DESC
SKIP $offset LIMIT $limit
"""

CUSTOMER_DETAIL = """
MATCH (c:Customer {id: $customer_id})<-[:PLACED_BY]-(:Order)
      -[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (c)<-[:PLACED_BY]-(o:Order)-[:BELONGS_TO]->(:Company {id: $company_id})
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
WITH c, collect(DISTINCT CASE WHEN p IS NULL THEN NULL
    ELSE {product_id: p.id, name: p.name, code: p.code} END) AS raw_products
RETURN
    c.id AS customer_id,
    c.name AS name,
    c.email AS email,
    c.document AS document,
    c.rfm_segment AS rfm_segment,
    c.rfm_score AS rfm_score,
    c.rfm_recency_days AS rfm_recency_days,
    c.rfm_frequency AS rfm_frequency,
    c.rfm_monetary AS rfm_monetary,
    c.last_order_at AS last_order_at,
    c.city_name AS city_name,
    c.state_initials AS state_initials,
    [x IN raw_products WHERE x IS NOT NULL] AS products_purchased
"""
