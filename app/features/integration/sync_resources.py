"""Coordinates sync engines for the resources enabled on an integration."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.features.integration.sync_state import RESOURCE_ORDERS, RESOURCE_PRODUCTS
from app.features.order.sync_engine import OrderSyncResult, run_order_sync
from app.features.product.sync_engine import ProductSyncResult, run_product_sync

SUPPORTED_SYNC_RESOURCES = {RESOURCE_ORDERS, RESOURCE_PRODUCTS}
DEFAULT_SYNC_RESOURCES = [RESOURCE_ORDERS]


def enabled_sync_resources(params: dict[str, Any]) -> list[str]:
    raw = params.get("resources")
    if raw is None:
        return DEFAULT_SYNC_RESOURCES
    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = [item for item in raw if isinstance(item, str)]
    else:
        return DEFAULT_SYNC_RESOURCES

    resources = [resource for resource in candidates if resource in SUPPORTED_SYNC_RESOURCES]
    return resources or DEFAULT_SYNC_RESOURCES


@dataclass
class IntegrationResourceSyncResult:
    resource: str
    pages_processed: int
    records_upserted: int


async def run_enabled_resource_syncs(
    integration_id: UUID,
    params: dict[str, Any],
    page_size: int = 100,
) -> list[IntegrationResourceSyncResult]:
    results: list[IntegrationResourceSyncResult] = []
    for resource in enabled_sync_resources(params):
        if resource == RESOURCE_ORDERS:
            order_result = await run_order_sync(integration_id, page_size=page_size)
            results.append(_order_result(order_result))
        elif resource == RESOURCE_PRODUCTS:
            product_result = await run_product_sync(integration_id, page_size=page_size)
            results.append(_product_result(product_result))
    return results


def _order_result(result: OrderSyncResult) -> IntegrationResourceSyncResult:
    return IntegrationResourceSyncResult(
        resource=RESOURCE_ORDERS,
        pages_processed=result.pages_processed,
        records_upserted=result.orders_upserted,
    )


def _product_result(result: ProductSyncResult) -> IntegrationResourceSyncResult:
    return IntegrationResourceSyncResult(
        resource=RESOURCE_PRODUCTS,
        pages_processed=result.pages_processed,
        records_upserted=result.products_upserted,
    )
