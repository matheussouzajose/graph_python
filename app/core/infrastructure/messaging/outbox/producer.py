"""Outbox-backed EventProducer.

Satisfies the same `EventProducer` Protocol as `RedisStreamProducer`, so
business code (the service) keeps calling `producer.publish(event)` and
never learns it went to a table instead of the stream.

The insert reuses the request-scoped session — it is flushed but NOT
committed here. `get_session` owns the transaction, so the event row and
the domain change commit atomically (or roll back together).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.messaging.base import Event
from app.core.infrastructure.messaging.outbox.orm import OutboxEventORM


class OutboxEventProducer:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish(self, event: Event) -> None:
        self._session.add(
            OutboxEventORM(
                name=event.name,
                payload=event.payload,
                occurred_at=event.occurred_at,
            )
        )
        await self._session.flush()
