"""Provider-agnostic messaging contracts.

The rest of the app talks to these interfaces, never to Redis/SQS/RabbitMQ
directly. To move off Redis tomorrow you write a new class that satisfies
these Protocols and swap it in the wiring — producers, handlers and
business code stay untouched.

    Event         -> a thing that happened (name + JSON payload)
    EventProducer -> publishes an Event to a stream/queue/topic
    EventHandler  -> reacts to a consumed Event
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass
class Event:
    name: str  # e.g. "video.created"
    payload: dict[str, Any]  # JSON-serializable
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventProducer(Protocol):
    async def publish(self, event: Event) -> None: ...


class EventHandler(Protocol):
    async def handle(self, event: Event) -> None: ...
