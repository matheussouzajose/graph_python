"""Event handlers.

For now the only handler just logs — the point is to prove the
producer/consumer plumbing end to end. Real work (kicking off the
download/transcription pipeline) goes here later, without touching the
consumer or the producer.
"""

import logging

from app.core.infrastructure.messaging.base import Event

logger = logging.getLogger(__name__)


class LoggingEventHandler:
    async def handle(self, event: Event) -> None:
        logger.info("Event received | name=%s payload=%s", event.name, event.payload)
