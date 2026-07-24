"""Business logic layer. `gds.py` calls are synchronous (same driver as
`app/core/infrastructure/database/neo4j.py`), so every call here goes through
`asyncio.to_thread` to avoid blocking the event loop during Neo4j I/O —
same reasoning as `order/graph_sync.py`.
"""

from __future__ import annotations

import asyncio

from app.features.graph_algorithms.gds import (
    recommend_by_customer,
    recommend_by_product,
    run_all_batch_algorithms,
    run_association_rules,
    run_customer_rfm,
    run_personalized_pagerank,
)

# Serializa execuções do job de algoritmos dentro deste processo. As mesmas
# projeções (`PRODUCT_GRAPH`/`CUSTOMER_GRAPH`) são recriadas (drop + project)
# a cada run — dois runs concorrentes disputariam a mesma projeção nomeada,
# então serializar em vez de rejeitar é mais simples e o segundo run só
# reprocessa o grafo já atualizado pelo primeiro.
_run_lock = asyncio.Lock()


def is_run_running() -> bool:
    return _run_lock.locked()


class GraphAlgorithmsService:
    async def run_all(self) -> dict:
        async with _run_lock:
            return await asyncio.to_thread(run_all_batch_algorithms)

    async def run_rfm(self) -> dict:
        return await asyncio.to_thread(run_customer_rfm)

    async def run_association_rules(
        self, min_support_count: int = 2, min_confidence: float = 0.05
    ) -> dict:
        return await asyncio.to_thread(run_association_rules, min_support_count, min_confidence)

    async def personalized_pagerank(self, product_ids: list[str], limit: int = 10) -> list[dict]:
        if not product_ids:
            return []
        return await asyncio.to_thread(run_personalized_pagerank, product_ids, limit)

    async def recommend_by_product(self, product_id: str, limit: int = 10) -> list[dict]:
        return await asyncio.to_thread(recommend_by_product, product_id, limit)

    async def recommend_by_customer(self, customer_id: str, limit: int = 10) -> list[dict]:
        return await asyncio.to_thread(recommend_by_customer, customer_id, limit)
