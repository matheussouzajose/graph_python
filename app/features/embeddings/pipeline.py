"""
Gera embeddings via OpenAI em lote e grava como propriedade do nó no Neo4j,
depois cria o vector index nativo para busca híbrida (vetorial + Cypher).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.infrastructure.database.neo4j import run_query, run_write_batch
from app.core.logger import logger
from app.features.embeddings.cypher import (
    FETCH_CUSTOMER_SUMMARIES,
    FETCH_ORDER_SUMMARIES,
    FETCH_PRODUCT_SUMMARIES,
    WRITE_CUSTOMER_EMBEDDINGS,
    WRITE_ORDER_EMBEDDINGS,
    WRITE_PRODUCT_EMBEDDINGS,
)
from app.features.embeddings.text_builder import (
    build_customer_text,
    build_order_text,
    build_product_text,
)

_client = OpenAI(api_key=settings.OPENAI_API_KEY)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30), reraise=True)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    # `dimensions` is passed explicitly (not left to the model's default) so
    # the vectors written here can never drift from what
    # `create_vector_indexes` configures on the Neo4j vector index.
    response = _client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
        dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
    )
    return [item.embedding for item in response.data]


def _process_entity(
    fetch_query: str,
    text_builder: Callable[[dict], str],
    write_query: str,
    entity_label: str,
    batch_size: int = 300,
) -> int:
    # `input` on the embeddings endpoint takes a batch of texts in a single
    # HTTP call — bigger batches mean fewer round trips, which dominate this
    # pipeline's wall-clock time far more than the embedding compute itself.
    # Order/Product summaries are short (well under 200 tokens each), so 300
    # stays comfortably under this model's per-request input-count (2048)
    # and token-budget limits.
    total_embedded = 0

    while True:
        rows = run_query(fetch_query, {"limit": batch_size})
        if not rows:
            break

        texts = [text_builder(row) for row in rows]
        embeddings = _embed_batch(texts)

        write_rows = [
            {"id": row["id"], "text": text, "embedding": embedding}
            for row, text, embedding in zip(rows, texts, embeddings, strict=True)
        ]
        run_write_batch(write_query, write_rows)

        total_embedded += len(rows)
        logger.info(
            "embeddings_batch_written",
            entity=entity_label,
            batch_size=len(rows),
            total=total_embedded,
        )

    return total_embedded


def embed_orders() -> int:
    return _process_entity(FETCH_ORDER_SUMMARIES, build_order_text, WRITE_ORDER_EMBEDDINGS, "Order")


def embed_products() -> int:
    return _process_entity(
        FETCH_PRODUCT_SUMMARIES, build_product_text, WRITE_PRODUCT_EMBEDDINGS, "Product"
    )


def embed_customers() -> int:
    return _process_entity(
        FETCH_CUSTOMER_SUMMARIES, build_customer_text, WRITE_CUSTOMER_EMBEDDINGS, "Customer"
    )


def create_vector_indexes() -> None:
    """Cria os vector indexes nativos do Neo4j sobre as propriedades de embedding."""
    run_query(
        f"""
        CREATE VECTOR INDEX order_embedding_index IF NOT EXISTS
        FOR (o:Order) ON (o.text_embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {settings.OPENAI_EMBEDDING_DIMENSIONS},
            `vector.similarity_function`: 'cosine'
        }}}}
        """
    )
    run_query(
        f"""
        CREATE VECTOR INDEX product_embedding_index IF NOT EXISTS
        FOR (p:Product) ON (p.text_embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {settings.OPENAI_EMBEDDING_DIMENSIONS},
            `vector.similarity_function`: 'cosine'
        }}}}
        """
    )
    run_query(
        f"""
        CREATE VECTOR INDEX customer_embedding_index IF NOT EXISTS
        FOR (c:Customer) ON (c.text_embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {settings.OPENAI_EMBEDDING_DIMENSIONS},
            `vector.similarity_function`: 'cosine'
        }}}}
        """
    )
    logger.info("vector_indexes_created")


def run_embedding_pipeline() -> dict:
    """Orders, Products e Customers são embedados em paralelo — são
    queries/escritas totalmente independentes (nós e propriedades
    diferentes), então rodar em threads separadas sobrepõe a espera de rede
    de uma com a das outras em vez de pagar as três em série."""
    logger.info("embedding_pipeline_started")

    with ThreadPoolExecutor(max_workers=3) as executor:
        orders_future = executor.submit(embed_orders)
        products_future = executor.submit(embed_products)
        customers_future = executor.submit(embed_customers)
        order_count = orders_future.result()
        product_count = products_future.result()
        customer_count = customers_future.result()

    create_vector_indexes()
    logger.info(
        "embedding_pipeline_complete",
        orders=order_count,
        products=product_count,
        customers=customer_count,
    )
    return {
        "orders_embedded": order_count,
        "products_embedded": product_count,
        "customers_embedded": customer_count,
    }
