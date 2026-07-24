"""Orquestra a projeção Postgres -> Neo4j: pagina pedidos já persistidos em
`orders` (ver `order/repository.py`), acumula em lotes, normaliza
(`graph_normalizer.py`) e grava via UNWIND (`graph_cypher.py`).

Diferente do sync ERP->Postgres (`sync_engine.py`), aqui a fonte já é o
nosso próprio banco — não há paginação por cursor de terceiro, só
offset/limit incremental sobre `OrderRepository.list`.

Estratégia de resiliência (mesma do pipeline de referência que motivou este
módulo):
1. Normalização de cada pedido é isolada em try/except — 1 pedido malformado
   não derruba o lote inteiro, só é logado e pulado.
2. Se o lote inteiro falhar ao gravar (ex: erro de conexão no meio), o
   pipeline tenta de novo linha a linha para isolar exatamente qual pedido
   está causando o problema, sem perder o restante do lote.

`run_write_batch` (neo4j.py) é síncrono; toda chamada passa por
`asyncio.to_thread` para não bloquear o event loop enquanto o driver do
Neo4j faz I/O de rede.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.infrastructure.database.neo4j import run_write_batch
from app.core.infrastructure.database.session import AsyncSessionFactory
from app.core.logger import logger
from app.features.order.graph_cypher import (
    INGEST_ADDRESSES_BATCH,
    INGEST_COUPONS_BATCH,
    INGEST_ORDERS_BATCH,
    INGEST_PAYMENTS_BATCH,
    INGEST_PRODUCTS_BATCH,
    INGEST_SKUS_BATCH,
)
from app.features.order.graph_normalizer import (
    normalize_address_row,
    normalize_coupon_row,
    normalize_order_row,
    normalize_payment_row,
    normalize_product_rows,
    normalize_sku_rows,
)
from app.features.order.orm import OrderORM
from app.features.order.repository import OrderRepository

DEFAULT_PAGE_SIZE = 200
DEFAULT_BATCH_SIZE = 500

# Serializa execuções de run_graph_sync dentro deste processo. Sem isso, dois
# triggers próximos (ex: clique duplo, retry do cliente) rodam em paralelo e
# competem pra criar os mesmos nós novos (Order/Payment/...) ao mesmo tempo —
# constraint de unicidade não gera duplicata, mas contenção de lock no Neo4j
# pode derrubar a escrita de um dos lados. Serializar em vez de rejeitar o
# segundo trigger: mais simples, e o segundo run só reprocessa o que já foi
# escrito (MERGE é idempotente), sem custo além do tempo de espera.
_sync_lock = asyncio.Lock()


def is_graph_sync_running() -> bool:
    return _sync_lock.locked()


@dataclass
class BatchAccumulator:
    """Acumula linhas normalizadas até atingir o tamanho de lote configurado."""

    orders: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    skus: list[dict[str, Any]] = field(default_factory=list)
    addresses: list[dict[str, Any]] = field(default_factory=list)
    payments: list[dict[str, Any]] = field(default_factory=list)
    coupons: list[dict[str, Any]] = field(default_factory=list)
    order_count: int = 0

    def add(self, order: OrderORM) -> None:
        self.orders.append(normalize_order_row(order))
        self.products.extend(normalize_product_rows(order))
        self.skus.extend(normalize_sku_rows(order))

        address_row = normalize_address_row(order)
        if address_row:
            self.addresses.append(address_row)

        self.payments.append(normalize_payment_row(order))

        coupon_row = normalize_coupon_row(order)
        if coupon_row:
            self.coupons.append(coupon_row)

        self.order_count += 1

    def is_full(self, batch_size: int) -> bool:
        return self.order_count >= batch_size

    def is_empty(self) -> bool:
        return self.order_count == 0


async def _flush_batch(batch: BatchAccumulator) -> None:
    """Grava o lote no Neo4j. Em caso de erro, tenta isolar pedido a pedido."""
    query_map = [
        (INGEST_ORDERS_BATCH, batch.orders, "orders"),
        (INGEST_PRODUCTS_BATCH, batch.products, "products"),
        (INGEST_SKUS_BATCH, batch.skus, "skus"),
        (INGEST_ADDRESSES_BATCH, batch.addresses, "addresses"),
        (INGEST_PAYMENTS_BATCH, batch.payments, "payments"),
        (INGEST_COUPONS_BATCH, batch.coupons, "coupons"),
    ]

    for query, rows, label in query_map:
        if not rows:
            continue
        try:
            await asyncio.to_thread(run_write_batch, query, rows)
        except Exception as exc:
            logger.error(
                "graph_batch_write_failed", entity=label, rows_in_batch=len(rows), error=str(exc)
            )
            await _flush_row_by_row(query, rows, label)


async def _flush_row_by_row(query: str, rows: list[dict[str, Any]], label: str) -> None:
    """Fallback: isola qual linha exata está causando o erro no lote."""
    failures = 0
    for row in rows:
        try:
            await asyncio.to_thread(run_write_batch, query, [row])
        except Exception as exc:
            failures += 1
            logger.error(
                "graph_row_write_failed",
                entity=label,
                row_id=row.get("id") or row.get("order_id"),
                error=str(exc),
            )
    logger.warning(
        "graph_row_by_row_fallback_complete", entity=label, total=len(rows), failures=failures
    )


async def run_graph_sync(
    integration_id: UUID | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, int]:
    """Composition root: pagina `orders` no Postgres e projeta cada página no
    grafo. Abre uma sessão nova por página (somente leitura) em vez de
    segurar uma sessão só pro run inteiro — igual ao motivo em
    `sync_engine.py`, mas aqui é só pra não prender uma conexão do pool
    ociosa durante um write no Neo4j que pode demorar.

    Serializado por `_sync_lock`: um segundo trigger enquanto este run ainda
    está de pé espera em vez de rodar em paralelo (ver comentário no lock)."""
    async with _sync_lock:
        batch = BatchAccumulator()
        offset = 0
        total_processed = 0
        total_failed_normalization = 0

        while True:
            async with AsyncSessionFactory() as session:
                orders = await OrderRepository(session).list(
                    integration_id=integration_id, limit=page_size, offset=offset
                )
            if not orders:
                break

            for order in orders:
                try:
                    batch.add(order)
                except Exception as exc:
                    total_failed_normalization += 1
                    logger.error(
                        "order_normalization_failed", order_id=str(order.id), error=str(exc)
                    )
                    continue

                if batch.is_full(batch_size):
                    await _flush_batch(batch)
                    total_processed += batch.order_count
                    batch = BatchAccumulator()

            offset += page_size

        if not batch.is_empty():
            await _flush_batch(batch)
            total_processed += batch.order_count

        summary = {
            "total_processed": total_processed,
            "total_failed_normalization": total_failed_normalization,
        }
        logger.info("graph_sync_complete", **summary)
        return summary
