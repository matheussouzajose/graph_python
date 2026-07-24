"""ORM model for the transactional outbox table.

Each row is one event awaiting delivery. It is written in the SAME
transaction as the domain change that produced it, and cleared (marked
published) by the relay once it reaches the real stream.

`published_at IS NULL` means "still pending". The partial index makes the
relay's poll query cheap even when the table has accumulated a lot of
already-published rows.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class OutboxEventORM(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Partial index: the relay only ever scans pending rows.
    __table_args__ = (
        Index(
            "ix_outbox_events_pending",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
    )
