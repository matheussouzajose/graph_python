"""Consumes `integration.sync_requested` events (published by
`POST /integrations/{id}/sync`) from Redis Streams and runs the order sync
for the requested integration.

Runs as a standalone process, decoupled from the API:

    uv run python -m app.features.order.sync_consumer

Failures are caught and logged here, never re-raised — `RedisStreamConsumer`
only acks a message after `handle()` returns without error, and this
consumer has no dead-letter/reclaim logic for the pending-entries list, so
leaving a message unacked would just strand it forever instead of retrying
it. A failed sync is logged and the message acked; the next periodic
`OrderSyncWorker` round (or another manual trigger) will pick the
integration back up from its last checkpoint regardless.
"""

import asyncio
import logging
from uuid import UUID

from app.core.infrastructure.database.session import AsyncSessionFactory
from app.core.infrastructure.messaging.base import Event
from app.core.infrastructure.messaging.client import get_redis_client
from app.core.infrastructure.messaging.events import (
    INTEGRATION_EVENTS_STREAM,
    INTEGRATION_SYNC_REQUESTED,
)
from app.core.infrastructure.messaging.redis_stream import RedisStreamConsumer
from app.features.integration.repository import IntegrationRepository
from app.features.integration.sync_resources import run_enabled_resource_syncs

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "order-sync"


class OrderSyncEventHandler:
    async def handle(self, event: Event) -> None:
        if event.name != INTEGRATION_SYNC_REQUESTED:
            return
        try:
            integration_id = UUID(event.payload["integration_id"])
            async with AsyncSessionFactory() as session:
                integration = await IntegrationRepository(session).get(integration_id)
                params = integration.params if integration else {}
            results = await run_enabled_resource_syncs(integration_id, params)
            for result in results:
                logger.info(
                    "Synced integration %s/%s: %d page(s), %d record(s)",
                    integration_id,
                    result.resource,
                    result.pages_processed,
                    result.records_upserted,
                )
        except Exception:
            logger.exception("Failed processing sync-requested event: %s", event.payload)


if __name__ == "__main__":
    consumer = RedisStreamConsumer(
        client=get_redis_client(),
        stream=INTEGRATION_EVENTS_STREAM,
        group=CONSUMER_GROUP,
        consumer_name="order-sync-consumer-1",
        handler=OrderSyncEventHandler(),
    )
    asyncio.run(consumer.run())
