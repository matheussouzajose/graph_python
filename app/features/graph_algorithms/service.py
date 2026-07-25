"""Business logic layer. `gds.py` calls are synchronous (same driver as
`app/core/infrastructure/database/neo4j.py`), so every call here goes through
`asyncio.to_thread` to avoid blocking the event loop during Neo4j I/O —
same reasoning as `order/graph_sync.py`.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.features.graph_algorithms.gds import (
    recommend_by_customer,
    recommend_by_product,
    run_all_batch_algorithms,
    run_association_rules,
    run_customer_rfm,
    run_personalized_pagerank,
)

# Serializa execuções do job de algoritmos dentro deste processo, mesmo entre
# empresas diferentes. As projeções GDS (nomeadas por empresa, ver
# `gds.py::product_graph_name`/`customer_graph_name`) são recriadas (drop +
# project) a cada run — como o nome já inclui a empresa, dois runs de
# empresas diferentes não colidiriam na mesma projeção nomeada, mas o lock
# continua global por simplicidade (não é bug de segurança, só significa que
# o run de uma empresa espera o de outra terminar em vez de rodar em
# paralelo).
_run_lock = asyncio.Lock()


def is_run_running() -> bool:
    return _run_lock.locked()


class GraphAlgorithmsService:
    async def run_all(self, external_company_id: UUID) -> dict:
        async with _run_lock:
            return await asyncio.to_thread(run_all_batch_algorithms, str(external_company_id))

    async def run_rfm(self, external_company_id: UUID) -> dict:
        return await asyncio.to_thread(run_customer_rfm, str(external_company_id))

    async def run_association_rules(
        self,
        external_company_id: UUID,
        min_support_count: int = 2,
        min_confidence: float = 0.05,
    ) -> dict:
        return await asyncio.to_thread(
            run_association_rules, str(external_company_id), min_support_count, min_confidence
        )

    async def personalized_pagerank(
        self, product_ids: list[str], limit: int = 10, external_company_id: UUID | None = None
    ) -> list[dict]:
        if not product_ids:
            return []
        return await asyncio.to_thread(
            run_personalized_pagerank,
            product_ids,
            limit,
            str(external_company_id) if external_company_id is not None else None,
        )

    async def recommend_by_product(
        self, product_id: str, limit: int = 10, external_company_id: UUID | None = None
    ) -> list[dict]:
        return await asyncio.to_thread(
            recommend_by_product,
            product_id,
            limit,
            str(external_company_id) if external_company_id is not None else None,
        )

    async def recommend_by_customer(
        self, customer_id: str, limit: int = 10, external_company_id: UUID | None = None
    ) -> list[dict]:
        return await asyncio.to_thread(
            recommend_by_customer,
            customer_id,
            limit,
            str(external_company_id) if external_company_id is not None else None,
        )
