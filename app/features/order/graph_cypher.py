"""Queries em lote via UNWIND $rows AS row.

Por que isso importa em produção: cada query é 1 round-trip de rede.
Ingerir 200 pedidos com queries individuais = 200+ round-trips. Com UNWIND,
200 pedidos = 1 round-trip por tipo de entidade (~6 round-trips no total pro
lote inteiro). Isso é a diferença entre ingestão levar minutos ou horas em
volume real.

`row.id`/`row.order_id` é o `OrderORM.id` interno (UUID gerado por nós), não
o id bruto do ERP: é a única chave globalmente única entre integrations
diferentes (o mesmo `external_order_id` de duas empresas diferentes não tem
relação nenhuma entre si). `row.company_id`/`row.customer_id`/`row.seller_id`
seguem os ids que o próprio ERP atribui, porque são conceitos aninhados sob
o mesmo pedido/empresa e é isso que `graph_normalizer.py` extrai.
"""

INGEST_ORDERS_BATCH = """
UNWIND $rows AS row
MERGE (o:Order {id: row.id})
SET o.code = row.code,
    o.origin = row.origin,
    o.status = row.status,
    o.created_at = row.created_at,
    o.updated_at = row.updated_at,
    o.total_value = row.total_value,
    o.total_discount_value = row.total_discount_value,
    o.total_discount_rate = row.total_discount_rate,
    o.survey_note = row.survey_note,
    o.survey_comment = row.survey_comment,
    o.is_unified = row.is_unified

MERGE (comp:Company {id: row.company_id})
MERGE (o)-[:BELONGS_TO]->(comp)

MERGE (cust:Customer {id: row.customer_id})
SET cust.name = row.customer_name,
    cust.document = row.customer_document,
    cust.email = row.customer_email,
    cust.phone = row.customer_phone,
    cust.company_name = row.customer_company_name
MERGE (o)-[:PLACED_BY]->(cust)

MERGE (sel:Seller {id: row.seller_id})
SET sel.name = row.seller_name,
    sel.lastname = row.seller_lastname,
    sel.email = row.seller_email
MERGE (o)-[:SOLD_BY]->(sel)

FOREACH (_ IN CASE WHEN row.status IS NOT NULL THEN [1] ELSE [] END |
    MERGE (st:OrderStatus {name: row.status})
    MERGE (o)-[:HAS_STATUS {at: row.updated_at}]->(st)
)
"""

INGEST_PRODUCTS_BATCH = """
UNWIND $rows AS row
MATCH (o:Order {id: row.order_id})
MERGE (p:Product {id: row.product_id})
SET p.integration_id = row.integration_id,
    p.code = row.code,
    p.name = row.name,
    p.image = row.image,
    p.price = row.price,
    p.price_promotional = row.price_promotional,
    p.promotion = row.promotion,
    p.weight = row.weight,
    p.height = row.height,
    p.width = row.width,
    p.length = row.length

MERGE (o)-[c:CONTAINS]->(p)
SET c.reserved = row.reserved,
    c.requested = row.requested,
    c.added = row.added,
    c.status = row.status
"""

INGEST_SKUS_BATCH = """
UNWIND $rows AS row
MATCH (p:Product {id: row.product_id})
MERGE (color:Color {id: row.color_id})
SET color.name = row.color_name, color.hex_code = row.color_code

MERGE (size:Size {id: row.size_id})
SET size.name = row.size_name

MERGE (sku:SKU {id: row.sku_id})
SET sku.sku = row.sku_code,
    sku.requested = row.requested,
    sku.reserved = row.reserved,
    sku.added = row.added

MERGE (p)-[:HAS_VARIANT]->(sku)
MERGE (sku)-[:HAS_COLOR]->(color)
MERGE (sku)-[:HAS_SIZE]->(size)
"""

INGEST_ADDRESSES_BATCH = """
UNWIND $rows AS row
MATCH (o:Order {id: row.order_id})
MERGE (addr:Address {id: row.address_key})
SET addr.cep = row.cep,
    addr.street = row.street,
    addr.number = row.number,
    addr.neighborhood = row.neighborhood
MERGE (o)-[:SHIPPED_TO]->(addr)

FOREACH (_ IN CASE WHEN row.city_name IS NOT NULL THEN [1] ELSE [] END |
    MERGE (city:City {name: row.city_name})
    MERGE (addr)-[:LOCATED_IN]->(city)
    FOREACH (__ IN CASE WHEN row.state_initials IS NOT NULL THEN [1] ELSE [] END |
        MERGE (state:State {initials: row.state_initials})
        MERGE (city)-[:IN_STATE]->(state)
    )
)
"""

INGEST_PAYMENTS_BATCH = """
UNWIND $rows AS row
MATCH (o:Order {id: row.order_id})
MERGE (pay:Payment {id: row.payment_id})
SET pay.method = row.method,
    pay.type = row.type,
    pay.is_paid = row.is_paid,
    pay.paid_at = row.paid_at,
    pay.transaction_id = row.transaction_id,
    pay.value = row.value,
    pay.taxes = row.taxes,
    pay.net_value = row.net_value,
    pay.card_brand = row.card_brand
MERGE (o)-[:PAID_VIA]->(pay)

MERGE (baddr:Address {id: row.billing_address_key})
SET baddr.cep = row.b_cep,
    baddr.street = row.b_street,
    baddr.neighborhood = row.b_neighborhood
MERGE (pay)-[:BILLED_TO]->(baddr)

FOREACH (_ IN CASE WHEN row.b_city_name IS NOT NULL THEN [1] ELSE [] END |
    MERGE (city:City {name: row.b_city_name})
    MERGE (baddr)-[:LOCATED_IN]->(city)
    FOREACH (__ IN CASE WHEN row.b_state_initials IS NOT NULL THEN [1] ELSE [] END |
        MERGE (state:State {initials: row.b_state_initials})
        MERGE (city)-[:IN_STATE]->(state)
    )
)
"""

INGEST_COUPONS_BATCH = """
UNWIND $rows AS row
MATCH (o:Order {id: row.order_id})
MERGE (cp:Coupon {code: row.code})
SET cp.amount = row.amount,
    cp.discount = row.discount
MERGE (o)-[:USED_COUPON]->(cp)
"""
