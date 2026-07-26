"""Runs product sync for one integration using the same checkpoint pattern as orders."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.infrastructure.database.session import AsyncSessionFactory
from app.features.company.repository import CompanyRepository
from app.features.integration.erp.base import ERPClient, ProductPage
from app.features.integration.erp.factory import get_erp_client
from app.features.integration.repository import IntegrationRepository
from app.features.integration.sync_state import RESOURCE_PRODUCTS, IntegrationSyncStateRepository
from app.features.product.repository import ProductRepository


class IntegrationNotFoundError(Exception):
    """Raised when `run_product_sync` is called with an unknown integration_id."""


@dataclass
class ProductSyncResult:
    integration_id: UUID
    pages_processed: int
    products_upserted: int


class ProductSyncEngine:
    def __init__(
        self,
        client: ERPClient,
        session_factory: async_sessionmaker[AsyncSession],
        external_company_id: UUID,
    ) -> None:
        self._client = client
        self._session_factory = session_factory
        self._external_company_id = external_company_id

    async def run(self, integration_id: UUID, page_size: int = 100) -> ProductSyncResult:
        cursor = await self._load_cursor(integration_id)

        pages_processed = 0
        products_upserted = 0
        has_more = True

        while has_more:
            page = await self._client.fetch_products(cursor, page_size=page_size)
            cursor = page.next_cursor
            has_more = page.has_more
            products_upserted += await self._persist_page(integration_id, page, has_more)
            pages_processed += 1

        return ProductSyncResult(
            integration_id=integration_id,
            pages_processed=pages_processed,
            products_upserted=products_upserted,
        )

    async def _load_cursor(self, integration_id: UUID) -> str | None:
        async with self._session_factory() as session:
            state = await IntegrationSyncStateRepository(session).get(
                integration_id, RESOURCE_PRODUCTS
            )
            return state.cursor if state else None

    async def _persist_page(self, integration_id: UUID, page: ProductPage, has_more: bool) -> int:
        async with self._session_factory() as session, session.begin():
            upserted = await ProductRepository(session).upsert_many(
                integration_id, self._external_company_id, page.products
            )
            await IntegrationSyncStateRepository(session).save_cursor(
                integration_id,
                RESOURCE_PRODUCTS,
                page.next_cursor,
                status="running" if has_more else "idle",
            )
            return upserted


async def run_product_sync(integration_id: UUID, page_size: int = 100) -> ProductSyncResult:
    async with AsyncSessionFactory() as session:
        integration = await IntegrationRepository(session).get(integration_id)
        if integration is None:
            raise IntegrationNotFoundError(integration_id)

        company = await CompanyRepository(session).get(integration.company_id)
        assert company is not None, "integration.company_id is FK-enforced, ON DELETE CASCADE"

        client = get_erp_client(integration, company)
        external_company_id = company.external_company_id

    engine = ProductSyncEngine(
        client=client,
        session_factory=AsyncSessionFactory,
        external_company_id=external_company_id,
    )
    return await engine.run(integration_id, page_size=page_size)
