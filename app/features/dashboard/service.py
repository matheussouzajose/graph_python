"""Business logic layer for the dashboard's read-only aggregation endpoints.

Two data sources, deliberately not unified behind one repository: the ERP
sync checkpoint (`last_synced_at`) lives in Postgres (`integration_sync_state`,
written by `sync_engine.py`), while everything else — orders, products,
customers, algorithm run markers — is already projected into Neo4j by
`order/graph_sync.py` / `graph_algorithms/gds.py` / `embeddings/pipeline.py`.
Neo4j calls go through `asyncio.to_thread` for the same reason as
`graph_algorithms/service.py`: `run_query` is a synchronous driver call.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.neo4j import run_query
from app.features.dashboard import cypher
from app.features.dashboard.schemas import (
    AlgorithmRunStatus,
    BoughtTogetherPair,
    CustomerDetail,
    CustomerPurchasedProduct,
    CustomerSummary,
    IntegrationSyncStatus,
    OrderStatusCount,
    OverviewResponse,
    RfmSegmentSummary,
    SyncStatusResponse,
    TopPageRankProduct,
    TopRevenueProduct,
    TopSellingProduct,
)
from app.features.integration.erp.factory import describe_sync_progress
from app.features.integration.repository import IntegrationRepository
from app.features.integration.sync_state import RESOURCE_ORDERS, IntegrationSyncStateRepository


def _native_dt(value: Any) -> datetime | None:
    """Neo4j's driver returns its own `DateTime`/`LocalDateTime` temporal types
    for `datetime` properties, not `datetime.datetime` — Pydantic won't accept
    those directly. `.to_native()` converts; already-native values (e.g. from
    Postgres) pass through untouched."""
    if value is None:
        return None
    to_native = getattr(value, "to_native", None)
    return to_native() if callable(to_native) else value


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._integration_repository = IntegrationRepository(session)
        self._sync_state_repository = IntegrationSyncStateRepository(session)

    async def get_overview(self, company_id: UUID, external_company_id: UUID) -> OverviewResponse:
        graph_company_id = str(external_company_id)
        totals_rows, status_rows, last_run_rows, sync_states = await asyncio.gather(
            asyncio.to_thread(run_query, cypher.OVERVIEW_TOTALS, {"company_id": graph_company_id}),
            asyncio.to_thread(run_query, cypher.ORDERS_BY_STATUS, {"company_id": graph_company_id}),
            asyncio.to_thread(
                run_query, cypher.LAST_ALGORITHM_RUN, {"company_id": graph_company_id}
            ),
            self._sync_state_repository.list_all(),
        )
        totals = totals_rows[0] if totals_rows else {}
        integrations = await self._integration_repository.list(company_id=company_id, limit=1000)
        integration_ids = {integration.id for integration in integrations}
        last_order_sync_at = max(
            (
                state.last_synced_at
                for state in sync_states
                if state.integration_id in integration_ids and state.last_synced_at is not None
            ),
            default=None,
        )
        last_algorithms_run_at = (
            _native_dt(last_run_rows[0]["computed_at"]) if last_run_rows else None
        )

        return OverviewResponse(
            total_revenue=totals.get("total_revenue") or 0.0,
            total_orders=totals.get("total_orders") or 0,
            average_ticket=totals.get("average_ticket") or 0.0,
            unique_customers=totals.get("unique_customers") or 0,
            products_sold=totals.get("products_sold") or 0,
            orders_by_status=[
                OrderStatusCount(status=row["status"], count=row["count"]) for row in status_rows
            ],
            last_order_sync_at=last_order_sync_at,
            last_algorithms_run_at=last_algorithms_run_at,
        )

    async def top_selling_products(
        self, external_company_id: UUID, limit: int = 10
    ) -> list[TopSellingProduct]:
        rows = await asyncio.to_thread(
            run_query,
            cypher.TOP_SELLING_PRODUCTS,
            {"company_id": str(external_company_id), "limit": limit},
        )
        return [
            TopSellingProduct(
                product_id=str(row["product_id"]),
                product_name=row["product_name"],
                product_code=row["product_code"],
                quantity_sold=row["quantity_sold"],
            )
            for row in rows
        ]

    async def top_revenue_products(
        self, external_company_id: UUID, limit: int = 10
    ) -> list[TopRevenueProduct]:
        rows = await asyncio.to_thread(
            run_query,
            cypher.TOP_REVENUE_PRODUCTS,
            {"company_id": str(external_company_id), "limit": limit},
        )
        return [
            TopRevenueProduct(
                product_id=str(row["product_id"]),
                product_name=row["product_name"],
                product_code=row["product_code"],
                revenue=row["revenue"],
            )
            for row in rows
        ]

    async def top_pagerank_products(
        self, external_company_id: UUID, limit: int = 10
    ) -> list[TopPageRankProduct]:
        rows = await asyncio.to_thread(
            run_query,
            cypher.TOP_PAGERANK_PRODUCTS,
            {"company_id": str(external_company_id), "limit": limit},
        )
        return [
            TopPageRankProduct(
                product_id=str(row["product_id"]),
                product_name=row["product_name"],
                product_code=row["product_code"],
                pagerank=row["pagerank"],
            )
            for row in rows
        ]

    async def bought_together(
        self, external_company_id: UUID, product_id: str | None = None, limit: int = 10
    ) -> list[BoughtTogetherPair]:
        company_id = str(external_company_id)
        if product_id:
            query, params = (
                cypher.BOUGHT_TOGETHER_FOR_PRODUCT,
                {
                    "company_id": company_id,
                    "product_id": product_id,
                    "limit": limit,
                },
            )
        else:
            query, params = cypher.BOUGHT_TOGETHER_ALL, {"company_id": company_id, "limit": limit}
        rows = await asyncio.to_thread(run_query, query, params)
        return [
            BoughtTogetherPair(
                product_id=str(row["product_id"]),
                product_name=row["product_name"],
                product_code=row["product_code"],
                related_product_id=str(row["related_product_id"]),
                related_product_name=row["related_product_name"],
                related_product_code=row["related_product_code"],
                support_count=row["support_count"],
                confidence=row["confidence"],
                lift=row["lift"],
            )
            for row in rows
        ]

    async def rfm_summary(self, external_company_id: UUID) -> list[RfmSegmentSummary]:
        rows = await asyncio.to_thread(
            run_query,
            cypher.RFM_SEGMENT_SUMMARY,
            {"company_id": str(external_company_id)},
        )
        return [RfmSegmentSummary(**row) for row in rows]

    async def list_customers(
        self,
        external_company_id: UUID,
        segment: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CustomerSummary]:
        rows = await asyncio.to_thread(
            run_query,
            cypher.CUSTOMERS_LIST,
            {
                "company_id": str(external_company_id),
                "segment": segment,
                "limit": limit,
                "offset": offset,
            },
        )
        return [
            CustomerSummary(
                customer_id=str(row["customer_id"]),
                name=row["name"],
                email=row["email"],
                document=row["document"],
                rfm_segment=row["rfm_segment"],
                rfm_score=row["rfm_score"],
                rfm_recency_days=row["rfm_recency_days"],
                rfm_frequency=row["rfm_frequency"],
                rfm_monetary=row["rfm_monetary"],
                last_order_at=_native_dt(row["last_order_at"]),
                city_name=row["city_name"],
                state_initials=row["state_initials"],
            )
            for row in rows
        ]

    async def get_customer(
        self, external_company_id: UUID, customer_id: str
    ) -> CustomerDetail | None:
        rows = await asyncio.to_thread(
            run_query,
            cypher.CUSTOMER_DETAIL,
            {"company_id": str(external_company_id), "customer_id": customer_id},
        )
        if not rows:
            return None
        row = rows[0]
        if row.get("customer_id") is None:
            return None
        return CustomerDetail(
            customer_id=str(row["customer_id"]),
            name=row["name"],
            email=row["email"],
            document=row["document"],
            rfm_segment=row["rfm_segment"],
            rfm_score=row["rfm_score"],
            rfm_recency_days=row["rfm_recency_days"],
            rfm_frequency=row["rfm_frequency"],
            rfm_monetary=row["rfm_monetary"],
            last_order_at=_native_dt(row["last_order_at"]),
            city_name=row["city_name"],
            state_initials=row["state_initials"],
            products_purchased=[
                CustomerPurchasedProduct(
                    product_id=str(product["product_id"]),
                    name=product["name"],
                    code=product["code"],
                )
                for product in row["products_purchased"]
            ],
        )

    async def sync_status(self, company_id: UUID, external_company_id: UUID) -> SyncStatusResponse:
        # `list_all()` and `list()` both use `self._session` — AsyncSession
        # forbids concurrent operations on the same session, so these two
        # stay sequential; only the Neo4j call (its own driver/connection)
        # can run alongside them.
        sync_states = await self._sync_state_repository.list_all()
        integrations = await self._integration_repository.list(company_id=company_id, limit=1000)
        algorithm_run_rows = await asyncio.to_thread(
            run_query, cypher.ALGORITHM_RUNS, {"company_id": str(external_company_id)}
        )
        states_by_integration_id = {
            state.integration_id: state
            for state in sync_states
            if state.resource == RESOURCE_ORDERS
        }

        # Iterate integrations, not sync_states, so an integration that has
        # never run a sync (no checkpoint row yet) still shows up — as
        # "never_synced" — instead of silently missing from the view.
        integration_statuses = []
        for integration in integrations:
            state = states_by_integration_id.get(integration.id)
            integration_statuses.append(
                IntegrationSyncStatus(
                    integration_id=str(integration.id),
                    integration_name=integration.name,
                    provider=integration.provider,
                    is_active=integration.is_active,
                    status=state.status if state else "never_synced",
                    last_synced_at=state.last_synced_at if state else None,
                    synced_until=(
                        describe_sync_progress(integration.provider, state.cursor)
                        if state
                        else None
                    ),
                )
            )

        return SyncStatusResponse(
            integrations=integration_statuses,
            algorithm_runs=[
                AlgorithmRunStatus(name=row["name"], computed_at=_native_dt(row["computed_at"]))
                for row in algorithm_run_rows
            ],
        )
