"""Business logic layer. Read-only: orders are written by the sync engine
(`app/features/order/sync_engine.py`), never through the HTTP API.
"""

from collections.abc import Sequence
from uuid import UUID

from app.features.order.orm import OrderORM
from app.features.order.repository import OrderRepository


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def get(self, order_id: UUID) -> OrderORM | None:
        return await self._repository.get(order_id)

    async def list(
        self, integration_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[OrderORM]:
        return await self._repository.list(
            integration_id=integration_id, limit=limit, offset=offset
        )
