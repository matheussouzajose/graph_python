"""
Chain final da via LOCAL: pega o contexto estruturado do retriever híbrido,
monta um prompt e chama o LLM. Prompt instrui explicitamente o modelo a
responder SOMENTE com base no contexto fornecido — reduz alucinação, que é
justamente o ganho central de Graph RAG sobre RAG vetorial puro.
"""

from __future__ import annotations

from collections.abc import Iterator

from openai import OpenAI

from app.core.config import settings
from app.core.logger import logger
from app.features.rag.retriever import hybrid_retrieve

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """Você é um assistente de análise de pedidos e produtos de e-commerce.
Responda a pergunta do usuário usando APENAS as informações fornecidas no
contexto abaixo. Se o contexto não tiver informação suficiente, diga
claramente que não encontrou dados suficientes — não invente números,
nomes de clientes ou produtos que não estejam no contexto.

Quando mencionar um pedido, cite o código dele (ex: "Pedido #590"). Quando
mencionar um produto, cite o código dele (ex: "Produto (código ABC123)").
"""


def _format_order_context(ctx: dict) -> str:
    total_value = ctx.get("total_value") or 0
    similarity_score = ctx.get("similarity_score") or 0
    return (
        f"- Pedido #{ctx.get('order_code')} (status: {ctx.get('status')}, "
        f"valor: R$ {total_value:.2f})\n"
        f"  Cliente: {ctx.get('customer_name')} "
        f"(segmento RFM: {ctx.get('customer_segment')}, "
        f"comunidade: {ctx.get('customer_community')})\n"
        f"  Produtos: {', '.join(ctx.get('products') or [])}\n"
        f"  Produtos relacionados no catálogo: "
        f"{', '.join(ctx.get('similar_products') or []) or 'nenhum'}\n"
        f"  Score de recuperação: {similarity_score:.3f}"
    )


def _format_product_context(ctx: dict) -> str:
    price = ctx.get("price") or 0
    price_promotional = ctx.get("price_promotional")
    pagerank = ctx.get("pagerank")
    similarity_score = ctx.get("similarity_score") or 0

    price_line = f"  Preço: R$ {price:.2f}"
    if price_promotional:
        price_line += f" (promocional: R$ {price_promotional:.2f})"

    lines = [
        f"- Produto: {ctx.get('product_name')} (código {ctx.get('product_code')})",
        price_line,
    ]
    colors = ctx.get("colors") or []
    if colors:
        lines.append(f"  Cores disponíveis: {', '.join(colors)}")
    sizes = ctx.get("sizes") or []
    if sizes:
        lines.append(f"  Tamanhos disponíveis: {', '.join(sizes)}")
    lines.append(
        f"  Produtos relacionados: {', '.join(ctx.get('similar_products') or []) or 'nenhum'}"
    )
    if pagerank is not None:
        lines.append(f"  Popularidade na rede de compras (pagerank): {pagerank:.4f}")
    lines.append(f"  Score de recuperação: {similarity_score:.3f}")

    return "\n".join(lines)


def _format_context(contexts: list[dict]) -> str:
    if not contexts:
        return "Nenhum pedido ou produto relevante encontrado."

    blocks = [
        _format_product_context(ctx)
        if ctx.get("context_type") == "product"
        else _format_order_context(ctx)
        for ctx in contexts
    ]

    return "\n\n".join(blocks)


def _build_messages(question: str, formatted_context: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Contexto:\n{formatted_context}\n\nPergunta: {question}",
        },
    ]


def _build_sources(contexts: list[dict]) -> list[dict]:
    return [
        {
            "order_code": c.get("order_code"),
            "product_code": c.get("product_code"),
            "score": c.get("similarity_score"),
        }
        for c in contexts
    ]


def ask(question: str, top_k: int = 5) -> dict:
    contexts = hybrid_retrieve(question, top_k=top_k)
    formatted_context = _format_context(contexts)

    response = _client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=_build_messages(question, formatted_context),
        temperature=0.1,  # baixa temperatura: queremos respostas ancoradas nos fatos, não criativas
    )

    answer = response.choices[0].message.content
    logger.info("rag_query_answered", question=question, contexts_used=len(contexts))

    return {
        "answer": answer,
        "sources": _build_sources(contexts),
    }


def ask_stream(question: str, top_k: int = 5) -> Iterator[dict]:
    """Variante em streaming de `ask`. A recuperação (`hybrid_retrieve`) não é
    token a token — só a geração da resposta final é, então `sources` sai
    inteiro num único evento `meta` antes do primeiro `token`, permitindo o
    consumidor já renderizar as fontes enquanto o texto ainda está chegando."""
    contexts = hybrid_retrieve(question, top_k=top_k)
    formatted_context = _format_context(contexts)

    yield {"type": "meta", "sources": _build_sources(contexts)}

    stream = _client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=_build_messages(question, formatted_context),
        temperature=0.1,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield {"type": "token", "text": delta}

    logger.info("rag_query_answered_stream", question=question, contexts_used=len(contexts))
