"""Queries sobre o grafo Order/Product/Customer já projetado por
`order/graph_sync.py` — mesmos labels/relacionamentos usados em
`order/graph_cypher.py` (BELONGS_TO, PLACED_BY, SOLD_BY, CONTAINS,
SHIPPED_TO, LOCATED_IN, IN_STATE, USED_COUPON, HAS_VARIANT, HAS_COLOR,
HAS_SIZE). `city_name`/`state_initials`/`rfm_*` em `FETCH_CUSTOMER_SUMMARIES`
vêm de `graph_algorithms/gds.py::run_customer_rfm`, que denormaliza esses
campos direto no nó `Customer` — sem RFM/geografia calculados ainda, esses
campos saem `NULL` e o texto do cliente fica mais pobre, mas não quebra.

`WHERE o.text_embedding IS NULL` / `WHERE p.text_embedding IS NULL` /
`WHERE c.text_embedding IS NULL` faz o fetch já vir só com o que falta
embedar — a mesma query, chamada em loop, converge sozinha sem precisar de
um cursor/offset explícito.
"""

FETCH_ORDER_SUMMARIES = """
MATCH (o:Order)
OPTIONAL MATCH (o)-[:BELONGS_TO]->(comp:Company)
OPTIONAL MATCH (o)-[:PLACED_BY]->(cust:Customer)
OPTIONAL MATCH (o)-[:SOLD_BY]->(sel:Seller)
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
OPTIONAL MATCH (o)-[:SHIPPED_TO]->(addr:Address)
OPTIONAL MATCH (addr)-[:LOCATED_IN]->(city:City)-[:IN_STATE]->(state:State)
OPTIONAL MATCH (o)-[:USED_COUPON]->(coupon:Coupon)
WHERE o.text_embedding IS NULL
WITH o, comp, cust, sel, city, state, coupon, collect(DISTINCT p.name) AS product_names
RETURN
    o.id AS id,
    o.code AS code,
    o.status AS status,
    o.origin AS origin,
    o.total_value AS total_value,
    o.survey_note AS survey_note,
    o.survey_comment AS survey_comment,
    cust.name AS customer_name,
    cust.company_name AS customer_company_name,
    sel.name AS seller_name,
    sel.lastname AS seller_lastname,
    city.name AS city_name,
    state.initials AS state_initials,
    coupon.code AS coupon_code,
    product_names
LIMIT $limit
"""

FETCH_PRODUCT_SUMMARIES = """
MATCH (p:Product)
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_COLOR]->(color:Color)
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(:SKU)-[:HAS_SIZE]->(size:Size)
WHERE p.text_embedding IS NULL
WITH p, collect(DISTINCT color.name) AS colors, collect(DISTINCT size.name) AS sizes
RETURN
    p.id AS id, p.name AS name, p.code AS code,
    p.price AS price, p.price_promotional AS price_promotional,
    colors, sizes
LIMIT $limit
"""

FETCH_CUSTOMER_SUMMARIES = """
MATCH (c:Customer)
WHERE c.text_embedding IS NULL
OPTIONAL MATCH (c)<-[:PLACED_BY]-(:Order)-[:CONTAINS]->(p:Product)
WITH c, collect(DISTINCT p.name)[0..10] AS product_names
RETURN
    c.id AS id,
    c.name AS name,
    c.document AS document,
    c.rfm_segment AS rfm_segment,
    c.rfm_score AS rfm_score,
    c.rfm_recency_days AS rfm_recency_days,
    c.rfm_frequency AS rfm_frequency,
    c.rfm_monetary AS rfm_monetary,
    c.city_name AS city_name,
    c.state_initials AS state_initials,
    product_names
LIMIT $limit
"""

WRITE_ORDER_EMBEDDINGS = """
UNWIND $rows AS row
MATCH (o:Order {id: row.id})
SET o.text_embedding = row.embedding, o.embedding_text = row.text
"""

WRITE_PRODUCT_EMBEDDINGS = """
UNWIND $rows AS row
MATCH (p:Product {id: row.id})
SET p.text_embedding = row.embedding, p.embedding_text = row.text
"""

WRITE_CUSTOMER_EMBEDDINGS = """
UNWIND $rows AS row
MATCH (c:Customer {id: row.id})
SET c.text_embedding = row.embedding, c.embedding_text = row.text
"""
