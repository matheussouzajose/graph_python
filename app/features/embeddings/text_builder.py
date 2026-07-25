"""
Constrói a representação textual de cada Order/Product/Customer que vai
virar embedding. Essa etapa é o que conecta a estrutura de grafo ao mundo de
busca vetorial — sem texto bem escrito aqui, a busca semântica do RAG fica
ruim mesmo com o grafo bem modelado.
"""

from __future__ import annotations


def build_order_text(order_summary: dict) -> str:
    """
    Recebe um dict já "achatado" (via query Cypher) com os principais
    atributos do pedido e seus relacionados, e monta um texto denso e legível.
    """
    parts = [
        f"Pedido #{order_summary.get('code')}.",
        f"Cliente: {order_summary.get('customer_name')} "
        f"({order_summary.get('customer_company_name') or 'pessoa física/PJ não identificada'}).",
        f"Vendedor: {order_summary.get('seller_name')} "
        f"{order_summary.get('seller_lastname') or ''}.",
        f"Status atual: {order_summary.get('status')}.",
        f"Origem do pedido: {order_summary.get('origin')}.",
    ]

    products = order_summary.get("product_names") or []
    if products:
        parts.append(f"Produtos: {', '.join(products)}.")

    if order_summary.get("city_name"):
        state_initials = order_summary.get("state_initials", "")
        parts.append(f"Entrega em {order_summary.get('city_name')}/{state_initials}.")

    if order_summary.get("coupon_code"):
        parts.append(f"Cupom utilizado: {order_summary.get('coupon_code')}.")

    total_value = order_summary.get("total_value") or 0
    parts.append(f"Valor total: R$ {total_value:.2f}.")

    if order_summary.get("survey_note") is not None:
        parts.append(
            f"Avaliação do cliente: nota {order_summary.get('survey_note')}"
            + (
                f", comentário: {order_summary.get('survey_comment')}."
                if order_summary.get("survey_comment")
                else "."
            )
        )

    return " ".join(parts)


def build_product_text(product_summary: dict) -> str:
    parts = [
        f"Produto: {product_summary.get('name')} (código {product_summary.get('code')}).",
    ]

    colors = product_summary.get("colors") or []
    sizes = product_summary.get("sizes") or []
    if colors:
        parts.append(f"Disponível nas cores: {', '.join(colors)}.")
    if sizes:
        parts.append(f"Tamanhos: {', '.join(sizes)}.")

    if product_summary.get("price"):
        parts.append(f"Preço: R$ {product_summary['price']:.2f}.")
    if product_summary.get("price_promotional"):
        parts.append(f"Preço promocional: R$ {product_summary['price_promotional']:.2f}.")

    return " ".join(parts)


def build_customer_text(customer_summary: dict) -> str:
    """`rfm_*`/`city_name`/`state_initials` vêm de `run_customer_rfm` — se o
    RFM ainda não rodou pra esse cliente, essas partes simplesmente não
    entram no texto (cliente ainda vira buscável por nome/produtos)."""
    parts = [f"Cliente: {customer_summary.get('name')}."]

    segment = customer_summary.get("rfm_segment")
    if segment:
        parts.append(f"Segmento RFM: {segment} (score {customer_summary.get('rfm_score')}).")

    frequency = customer_summary.get("rfm_frequency")
    if frequency is not None:
        monetary = customer_summary.get("rfm_monetary") or 0
        recency_days = customer_summary.get("rfm_recency_days")
        parts.append(
            f"Fez {frequency} pedido(s), totalizando R$ {monetary:.2f} em compras, "
            f"última compra há {recency_days} dia(s)."
        )

    if customer_summary.get("city_name"):
        state_initials = customer_summary.get("state_initials") or ""
        parts.append(f"Localização: {customer_summary.get('city_name')}/{state_initials}.")

    products = customer_summary.get("product_names") or []
    if products:
        parts.append(f"Produtos mais comprados: {', '.join(products)}.")

    return " ".join(parts)
