"""Queries de leitura sobre o grafo Order/Product/Customer já projetado por
`order/graph_sync.py` e enriquecido por `graph_algorithms/gds.py`
(`pagerank`, `SIMILAR_TO`, `BOUGHT_WITH`, `rfm_*`) e `embeddings/pipeline.py`.

Nenhuma query aqui escreve no grafo — este módulo é só leitura agregada para
o dashboard, nunca reusado pelos jobs em batch (que têm suas próprias queries
em `graph_algorithms/gds.py` e `order/graph_cypher.py`).
"""

OVERVIEW_TOTALS = """
MATCH (o:Order)
WITH count(o) AS total_orders,
     sum(coalesce(o.total_value, 0.0)) AS total_revenue,
     avg(o.total_value) AS average_ticket
OPTIONAL MATCH (:Order)-[:PLACED_BY]->(c:Customer)
WITH total_orders, total_revenue, average_ticket, count(DISTINCT c) AS unique_customers
OPTIONAL MATCH (:Order)-[:CONTAINS]->(p:Product)
RETURN
    total_orders,
    total_revenue,
    coalesce(average_ticket, 0.0) AS average_ticket,
    unique_customers,
    count(DISTINCT p) AS products_sold
"""

ORDERS_BY_STATUS = """
MATCH (o:Order)
WHERE o.status IS NOT NULL
RETURN o.status AS status, count(o) AS count
ORDER BY count DESC
"""

LAST_ALGORITHM_RUN = """
MATCH (r:AlgorithmRun)
RETURN max(r.computed_at) AS computed_at
"""

ALGORITHM_RUNS = """
MATCH (r:AlgorithmRun)
RETURN r.name AS name, r.computed_at AS computed_at
ORDER BY r.computed_at DESC
"""

TOP_SELLING_PRODUCTS = """
MATCH (:Order)-[c:CONTAINS]->(p:Product)
WITH p, sum(coalesce(c.requested, 0)) AS quantity_sold
WHERE quantity_sold > 0
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, quantity_sold
ORDER BY quantity_sold DESC
LIMIT $limit
"""

TOP_REVENUE_PRODUCTS = """
MATCH (:Order)-[c:CONTAINS]->(p:Product)
WITH p, sum(coalesce(c.requested, 0) * coalesce(p.price_promotional, p.price, 0.0)) AS revenue
WHERE revenue > 0
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, revenue
ORDER BY revenue DESC
LIMIT $limit
"""

TOP_PAGERANK_PRODUCTS = """
MATCH (p:Product)
WHERE p.pagerank IS NOT NULL
RETURN p.id AS product_id, p.name AS product_name, p.code AS product_code, p.pagerank AS pagerank
ORDER BY p.pagerank DESC
LIMIT $limit
"""

BOUGHT_TOGETHER_ALL = """
MATCH (a:Product)-[b:BOUGHT_WITH]->(c:Product)
RETURN
    a.id AS product_id, a.name AS product_name, a.code AS product_code,
    c.id AS related_product_id, c.name AS related_product_name, c.code AS related_product_code,
    b.support_count AS support_count, b.confidence AS confidence, b.lift AS lift
ORDER BY b.lift DESC
LIMIT $limit
"""

BOUGHT_TOGETHER_FOR_PRODUCT = """
MATCH (a:Product {id: $product_id})-[b:BOUGHT_WITH]->(c:Product)
RETURN
    a.id AS product_id, a.name AS product_name, a.code AS product_code,
    c.id AS related_product_id, c.name AS related_product_name, c.code AS related_product_code,
    b.support_count AS support_count, b.confidence AS confidence, b.lift AS lift
ORDER BY b.lift DESC
LIMIT $limit
"""

RFM_SEGMENT_SUMMARY = """
MATCH (c:Customer)
WHERE c.rfm_segment IS NOT NULL
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
MATCH (c:Customer)
WHERE c.rfm_segment IS NOT NULL
  AND ($segment IS NULL OR c.rfm_segment = $segment)
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
    c.last_order_at AS last_order_at
ORDER BY c.rfm_score DESC
SKIP $offset LIMIT $limit
"""

CUSTOMER_DETAIL = """
MATCH (c:Customer {id: $customer_id})
OPTIONAL MATCH (c)<-[:PLACED_BY]-(:Order)-[:CONTAINS]->(p:Product)
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
    [x IN raw_products WHERE x IS NOT NULL] AS products_purchased
"""
