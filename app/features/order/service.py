"""Business logic layer. Read-only: orders are written by the sync engine
(`app/features/order/sync_engine.py`), never through the HTTP API.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.features.order.orm import OrderORM
from app.features.order.repository import OrderRepository


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def get(self, order_id: UUID) -> OrderORM | None:
        return await self._repository.get(order_id)

    async def get_for_company(self, order_id: UUID, company_id: UUID) -> OrderORM | None:
        return await self._repository.get_for_company(order_id, company_id)

    async def list(
        self, integration_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[OrderORM]:
        return await self._repository.list(
            integration_id=integration_id, limit=limit, offset=offset
        )

    async def list_for_company(
        self,
        company_id: UUID,
        integration_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[OrderORM]:
        return await self._repository.list_for_company(
            company_id=company_id,
            integration_id=integration_id,
            limit=limit,
            offset=offset,
        )

    async def list_filtered_for_company(
        self,
        company_id: UUID,
        filters: dict[str, list[str]],
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[OrderORM], int]:
        return await self._repository.list_filtered_for_company(
            company_id=company_id,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    async def filter_facets_for_company(
        self,
        company_id: UUID,
        filters: dict[str, list[str]],
        option_limit: int = 40,
    ) -> list[dict[str, Any]]:
        return await self._repository.filter_facets_for_company(
            company_id=company_id,
            filters=filters,
            option_limit=option_limit,
        )
