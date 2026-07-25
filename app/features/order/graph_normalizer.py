"""Achata um `OrderORM` (colunas + blobs JSONB do ERP) nas linhas que as
queries `UNWIND $rows` de `graph_cypher.py` esperam.

`customer_id`/`seller_id`/`product_id`/`sku_id`/`color_id`/`size_id` vêm
compostos como `f"{company_id}:{raw_id}"` (ver `_scoped`), não o ID bruto do
ERP — esses IDs são atribuídos pelo catálogo/ERP de *cada empresa*, não são
globalmente únicos. Sem o prefixo, duas empresas usando o mesmo provider de
ERP poderiam ter clientes/produtos com o mesmo ID bruto, e o `MERGE` por
`{id: ...}` em `graph_cypher.py` fundiria os dois num nó só — corrupção de
dado entre tenants, não só um problema de controle de acesso. `Order` já não
tinha esse problema porque usa o UUID interno (`OrderORM.id`), gerado por
nós, nunca o ID bruto do ERP; isso aqui é o mesmo tratamento estendido pros
nós que faltavam.

`address`/`payment.address` costumam vir sem `id` (a Vesti manda `null`) —
por isso `address_key`/`billing_address_key` caem para uma chave sintética
`f"{order_id}-shipping"`/`f"{order_id}-billing"` quando o ERP não dá um id
próprio, em vez de arriscar colidir endereços de pedidos diferentes sob o
mesmo nó. O mesmo vale para `payment_id`: `transaction.id` normalmente é
`null` em pagamentos manuais/não processados, então cai para
`f"{order_id}-payment"`. Esse fallback já é seguro (`order_id` é o UUID
interno, único globalmente); só o ramo "ERP deu um ID" desses dois ainda
compartilha o mesmo risco de colisão entre empresas que `Customer`/`Product`
tinham — não tratado nesta rodada, fica pra um follow-up.

`normalize_address_row` retorna `None` quando não há cep/rua/bairro algum
(pedido sem endereço de entrega, ex. retirada em loja) — nesse caso
`graph_sync.py` simplesmente não inclui a linha no lote, ao invés de criar
um nó `Address` vazio. `normalize_coupon_row` segue a mesma lógica para
pedidos sem cupom.
"""

from __future__ import annotations

from typing import Any

from app.features.order.orm import OrderORM


def _scoped(company_id: str, raw_id: Any) -> str | None:
    """Compõe um ID de catálogo (cliente/produto/vendedor/SKU/cor/tamanho)
    com a empresa dona dele, pra dois IDs brutos iguais de empresas
    diferentes nunca colidirem no `MERGE` do Neo4j."""
    return f"{company_id}:{raw_id}" if raw_id is not None else None


def normalize_order_row(order: OrderORM) -> dict[str, Any]:
    customer = order.customer or {}
    seller = order.seller or {}
    summary = order.summary or {}
    company_id = str(order.external_company_id)
    return {
        "id": str(order.id),
        "code": order.code,
        "origin": order.origin,
        "status": order.status,
        "created_at": order.external_created_at,
        "updated_at": order.external_updated_at,
        "total_value": summary.get("total_value"),
        "total_discount_value": summary.get("total_discount_value"),
        "total_discount_rate": summary.get("total_discount_rate"),
        "survey_note": order.survey_note,
        "survey_comment": order.survey_comment,
        "is_unified": order.is_unified,
        "company_id": company_id,
        "customer_id": _scoped(company_id, customer.get("id")),
        "customer_name": customer.get("name"),
        "customer_document": customer.get("document"),
        "customer_email": customer.get("email"),
        "customer_phone": customer.get("phone"),
        "customer_company_name": customer.get("company_name"),
        "seller_id": _scoped(company_id, seller.get("id")),
        "seller_name": seller.get("name"),
        "seller_lastname": seller.get("lastname"),
        "seller_email": seller.get("email"),
    }


def normalize_product_rows(order: OrderORM) -> list[dict[str, Any]]:
    # `MERGE (p:Product {id: row.product_id})` errors out on a null id — a
    # product entry without one can't become a node, so it's skipped rather
    # than crashing the whole batch (same reasoning as the SKU filter below).
    order_id = str(order.id)
    company_id = str(order.external_company_id)
    return [
        {
            "order_id": order_id,
            "product_id": _scoped(company_id, product.get("id")),
            "integration_id": product.get("integration_id"),
            "code": product.get("code"),
            "name": product.get("name"),
            "image": product.get("image"),
            "price": product.get("price"),
            "price_promotional": product.get("price_promotional"),
            "promotion": product.get("promotion"),
            "weight": product.get("weight"),
            "height": product.get("height"),
            "width": product.get("width"),
            "length": product.get("length"),
            "reserved": product.get("reserved"),
            "requested": product.get("requested"),
            "added": product.get("added"),
            "status": product.get("status"),
        }
        for product in order.products or []
        if product.get("id") is not None
    ]


def normalize_sku_rows(order: OrderORM) -> list[dict[str, Any]]:
    # `INGEST_SKUS_BATCH` does `MERGE` on `sku_id`, `color_id` and `size_id`
    # in the same statement — a null in any of the three makes Neo4j reject
    # the whole MERGE ("Cannot merge ... null property value for 'id'"), not
    # just one clause. Some `stocks[]` entries genuinely lack a color
    # or size (seen in production data), so those get skipped here instead
    # of round-tripping through the row-by-row fallback for an error that's
    # always going to happen.
    company_id = str(order.external_company_id)
    rows: list[dict[str, Any]] = []
    for product in order.products or []:
        product_id = product.get("id")
        if product_id is None:
            continue
        for stock in product.get("stocks") or []:
            sku_id = stock.get("id")
            color_id = stock.get("color_id")
            size_id = stock.get("size_id")
            if sku_id is None or color_id is None or size_id is None:
                continue
            rows.append(
                {
                    "product_id": _scoped(company_id, product_id),
                    "sku_id": _scoped(company_id, sku_id),
                    "sku_code": stock.get("sku"),
                    "requested": stock.get("requested"),
                    "reserved": stock.get("reserved"),
                    "added": stock.get("added"),
                    "color_id": _scoped(company_id, color_id),
                    "color_name": stock.get("color_name"),
                    "color_code": stock.get("color_code"),
                    "size_id": _scoped(company_id, size_id),
                    "size_name": stock.get("size_name"),
                }
            )
    return rows


def normalize_address_row(order: OrderORM) -> dict[str, Any] | None:
    address = order.address or {}
    cep = address.get("cep")
    street = address.get("street")
    neighborhood = address.get("neighborhood")
    if not cep and not street and not neighborhood:
        return None

    order_id = str(order.id)
    city = address.get("city") or {}
    state = address.get("state") or {}
    return {
        "order_id": order_id,
        "address_key": address.get("id") or f"{order_id}-shipping",
        "cep": cep,
        "street": street,
        "number": address.get("number"),
        "neighborhood": neighborhood,
        "city_name": city.get("name"),
        "state_initials": state.get("initials"),
    }


def normalize_payment_row(order: OrderORM) -> dict[str, Any]:
    payment = order.payment or {}
    transaction = payment.get("transaction") or {}
    card = payment.get("card") or {}
    billing_address = payment.get("address") or {}
    billing_city = billing_address.get("city") or {}
    billing_state = billing_address.get("state") or {}

    order_id = str(order.id)
    return {
        "order_id": order_id,
        "payment_id": transaction.get("id") or f"{order_id}-payment",
        "method": payment.get("method"),
        "type": payment.get("type"),
        "is_paid": payment.get("is_paid"),
        "paid_at": payment.get("paid_at"),
        "transaction_id": transaction.get("id"),
        "value": transaction.get("value"),
        "taxes": transaction.get("taxes"),
        "net_value": transaction.get("net_value"),
        "card_brand": card.get("brand"),
        "billing_address_key": billing_address.get("id") or f"{order_id}-billing",
        "b_cep": billing_address.get("cep"),
        "b_street": billing_address.get("street"),
        "b_neighborhood": billing_address.get("neighborhood"),
        "b_city_name": billing_city.get("name"),
        "b_state_initials": billing_state.get("initials"),
    }


def normalize_coupon_row(order: OrderORM) -> dict[str, Any] | None:
    coupon = (order.summary or {}).get("coupon") or {}
    code = coupon.get("code")
    if not code:
        return None
    return {
        "order_id": str(order.id),
        "code": code,
        "amount": coupon.get("amount"),
        "discount": coupon.get("discount"),
    }
