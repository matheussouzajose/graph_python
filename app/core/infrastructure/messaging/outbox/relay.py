"""Outbox relay — the "message relay" half of the pattern.

Polls `outbox_events` for pending rows, publishes each to the real stream,
and marks it published. All within one DB transaction per batch:

    SELECT ... WHERE published_at IS NULL
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED      -- lets many relays share the load
        LIMIT batch
    -> publish to stream
    -> set published_at = now()
    -> COMMIT

Delivery is at-least-once: if the process dies after publishing but before
the commit, the row stays pending and is republished next round. Consumers
must therefore be idempotent.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.sql.functions import now

from app.core.infrastructure.messaging.base import Event, EventProducer
from app.core.infrastructure.messaging.outbox.orm import OutboxEventORM

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        producer: EventProducer,
        batch: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._producer = producer
        self._batch = batch
        self._poll_interval = poll_interval
        self._running = False

    async def run(self) -> None:
        """Drain forever. Sleeps only when there is nothing pending."""
        self._running = True
        logger.info("Outbox relay started (batch=%d)", self._batch)
        while self._running:
            try:
                published = await self._drain_once()
            except Exception:
                logger.exception("Outbox relay batch failed; retrying")
                published = 0
            if published == 0:
                await asyncio.sleep(self._poll_interval)

    async def _drain_once(self) -> int:
        """Publish one batch of pending rows in a single transaction."""
        async with self._session_factory() as session, session.begin():
            stmt = (
                select(OutboxEventORM)
                .where(OutboxEventORM.published_at.is_(None))
                .order_by(OutboxEventORM.created_at)
                .limit(self._batch)
                .with_for_update(skip_locked=True)
            )
            rows = (await session.scalars(stmt)).all()
            for row in rows:
                await self._producer.publish(
                    Event(
                        name=row.name,
                        payload=row.payload,
                        occurred_at=row.occurred_at,
                    )
                )
                row.published_at = now()
            if rows:
                logger.info("Relayed %d outbox event(s)", len(rows))
            return len(rows)

    def stop(self) -> None:
        self._running = False
