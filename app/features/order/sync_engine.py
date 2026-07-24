"""Runs a full sync pass for one integration's orders: walks forward from
its last checkpoint until caught up, upserting every page as it goes.

Each page commits in its own transaction (see `_persist_page`) — a heavy
backfill can span hundreds of pages, and a crash mid-run must only lose the
one in-flight page, not the whole run. A single long-lived transaction for
the entire loop would defeat the checkpoint's whole purpose.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.infrastructure.database.session import AsyncSessionFactory
from app.features.company.repository import CompanyRepository
from app.features.integration.erp.base import ERPClient, OrderPage
from app.features.integration.erp.factory import get_erp_client
from app.features.integration.repository import IntegrationRepository
from app.features.integration.sync_state import RESOURCE_ORDERS, IntegrationSyncStateRepository
from app.features.order.repository import OrderRepository


class IntegrationNotFoundError(Exception):
    """Raised when `run_order_sync` is called with an unknown integration_id."""


@dataclass
class OrderSyncResult:
    integration_id: UUID
    pages_processed: int
    orders_upserted: int


class OrderSyncEngine:
    def __init__(
        self,
        client: ERPClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._client = client
        self._session_factory = session_factory

    async def run(self, integration_id: UUID, page_size: int = 100) -> OrderSyncResult:
        cursor = await self._load_cursor(integration_id)

        pages_processed = 0
        orders_upserted = 0
        has_more = True

        while has_more:
            page = await self._client.fetch_orders(cursor, page_size=page_size)
            cursor = page.next_cursor
            has_more = page.has_more
            orders_upserted += await self._persist_page(integration_id, page, has_more)
            pages_processed += 1

        return OrderSyncResult(
            integration_id=integration_id,
            pages_processed=pages_processed,
            orders_upserted=orders_upserted,
        )

    async def _load_cursor(self, integration_id: UUID) -> str | None:
        async with self._session_factory() as session:
            state = await IntegrationSyncStateRepository(session).get(
                integration_id, RESOURCE_ORDERS
            )
            return state.cursor if state else None

    async def _persist_page(self, integration_id: UUID, page: OrderPage, has_more: bool) -> int:
        async with self._session_factory() as session, session.begin():
            upserted = await OrderRepository(session).upsert_many(integration_id, page.orders)
            await IntegrationSyncStateRepository(session).save_cursor(
                integration_id,
                RESOURCE_ORDERS,
                page.next_cursor,
                status="running" if has_more else "idle",
            )
            return upserted


async def run_order_sync(integration_id: UUID, page_size: int = 100) -> OrderSyncResult:
    """Composition root: wires the ERP client and runs a full sync pass for
    one integration. Owns its own sessions throughout — do not pass in a
    request-scoped session, a multi-page sync must not share a single
    request's transaction lifecycle."""
    async with AsyncSessionFactory() as session:
        integration = await IntegrationRepository(session).get(integration_id)
        if integration is None:
            raise IntegrationNotFoundError(integration_id)

        company = await CompanyRepository(session).get(integration.company_id)
        assert company is not None, "integration.company_id is FK-enforced, ON DELETE CASCADE"

        client = get_erp_client(integration, company)

    engine = OrderSyncEngine(client=client, session_factory=AsyncSessionFactory)
    return await engine.run(integration_id, page_size=page_size)
