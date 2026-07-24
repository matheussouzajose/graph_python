"""Redis Streams implementation of the messaging contracts.

Why Redis Streams (and not plain pub/sub):
- messages are persisted in the stream, not lost if no one is listening;
- consumer groups give at-least-once delivery with explicit ACK, and let
  you scale to many consumers sharing the load.

The wire format is deliberately simple and provider-neutral: each stream
entry has two fields, `name` and `payload` (JSON). A future SQS/RabbitMQ
producer can use the exact same envelope.
"""

import asyncio
import json
import logging

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from app.core.infrastructure.messaging.base import Event, EventHandler

logger = logging.getLogger(__name__)


class RedisStreamProducer:
    """Publishes events to a single Redis Stream (XADD)."""

    def __init__(self, client: Redis, stream: str) -> None:
        self._client = client
        self._stream = stream

    async def publish(self, event: Event) -> None:
        await self._client.xadd(
            self._stream,
            {
                "name": event.name,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": json.dumps(event.payload),
            },
        )
        logger.debug("Published %s to stream %s", event.name, self._stream)


class RedisStreamConsumer:
    """Reads a Redis Stream via a consumer group and dispatches to a handler.

    Flow per message: read (XREADGROUP) -> handle -> ACK (XACK). If the
    handler raises, the message is NOT acked and will be redelivered.
    """

    def __init__(
        self,
        client: Redis,
        stream: str,
        group: str,
        consumer_name: str,
        handler: EventHandler,
        block_ms: int = 5000,
        batch: int = 10,
    ) -> None:
        self._client = client
        self._stream = stream
        self._group = group
        self._consumer_name = consumer_name
        self._handler = handler
        self._block_ms = block_ms
        self._batch = batch
        self._running = False

    async def _ensure_group(self) -> None:
        """Create the consumer group (and the stream) if it doesn't exist."""
        try:
            await self._client.xgroup_create(self._stream, self._group, id="0", mkstream=True)
            logger.info("Created group %s on %s", self._group, self._stream)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise  # group already exists is fine; anything else isn't

    async def run(self) -> None:
        """Consume forever. Stop by calling `stop()` from another task."""
        await self._ensure_group()
        self._running = True
        logger.info(
            "Consumer %s listening on %s (group %s)",
            self._consumer_name,
            self._stream,
            self._group,
        )
        while self._running:
            try:
                resp = await self._client.xreadgroup(
                    self._group,
                    self._consumer_name,
                    {self._stream: ">"},
                    count=self._batch,
                    block=self._block_ms,
                )
            except (ConnectionError, TimeoutError) as exc:
                # Transient Redis blip (dropped idle connection, network
                # hiccup). Don't die — redis-py reconnects on the next
                # command, so back off briefly and retry the read.
                logger.warning("Redis read failed (%s); retrying in 2s", exc)
                await asyncio.sleep(2)
                continue
            if not resp:
                continue  # block timed out, no new messages — loop again
            for _stream, messages in resp:
                for message_id, fields in messages:
                    await self._dispatch(message_id, fields)

    async def _dispatch(self, message_id: str, fields: dict) -> None:
        try:
            event = Event(
                name=fields["name"],
                payload=json.loads(fields["payload"]),
            )
            await self._handler.handle(event)
            await self._client.xack(self._stream, self._group, message_id)
        except Exception:
            # Not acked -> Redis keeps it pending for redelivery/inspection.
            logger.exception("Failed to handle message %s", message_id)

    def stop(self) -> None:
        self._running = False
