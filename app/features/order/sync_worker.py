"""Background worker that periodically syncs orders for every active
integration — mirrors `OutboxRelay`'s `run()`/`stop()` shape
(`app/core/infrastructure/messaging/outbox/relay.py`).

Runs as a standalone process, separate from the API:

    uv run python -m app.features.order.sync_worker

Each integration syncs independently and commits its own progress per page
(see `OrderSyncEngine`); one failing integration (bad credentials, ERP
outage) is logged and skipped, it never blocks the rest of the round or
crashes the worker.
"""

import asyncio
import logging

from app.core.infrastructure.database.session import AsyncSessionFactory
from app.features.integration.repository import IntegrationRepository
from app.features.order.sync_engine import run_order_sync

logger = logging.getLogger(__name__)


class OrderSyncWorker:
    def __init__(self, poll_interval: float = 300.0, page_size: int = 100) -> None:
        self._poll_interval = poll_interval
        self._page_size = page_size
        self._running = False

    async def run(self) -> None:
        """Sync every active integration, forever, sleeping `poll_interval`
        between rounds."""
        self._running = True
        logger.info("Order sync worker started (poll_interval=%.0fs)", self._poll_interval)
        while self._running:
            try:
                await self._run_once()
            except Exception:
                logger.exception("Order sync round failed; retrying next interval")
            await asyncio.sleep(self._poll_interval)

    async def _run_once(self) -> None:
        async with AsyncSessionFactory() as session:
            integrations = await IntegrationRepository(session).list_active()

        for integration in integrations:
            try:
                result = await run_order_sync(integration.id, page_size=self._page_size)
                logger.info(
                    "Synced integration %s: %d page(s), %d order(s)",
                    integration.id,
                    result.pages_processed,
                    result.orders_upserted,
                )
            except Exception:
                logger.exception("Failed syncing integration %s", integration.id)

    def stop(self) -> None:
        self._running = False


if __name__ == "__main__":
    asyncio.run(OrderSyncWorker().run())
