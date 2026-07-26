"""Per-integration, per-resource sync checkpoint.

`cursor` is opaque — its format is owned entirely by whichever `ERPClient`
produced it (see `erp/base.py`). `resource` lets one integration track
independent progress for multiple resource types (only `"orders"` exists
today; `"products"`/`"customers"` etc. would each get their own row).
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base

RESOURCE_ORDERS = "orders"
RESOURCE_PRODUCTS = "products"


class IntegrationSyncStateORM(Base):
    __tablename__ = "integration_sync_state"

    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "integrations.id", ondelete="CASCADE", name="fk_integration_sync_state_integration_id"
        ),
        primary_key=True,
    )
    resource: Mapped[str] = mapped_column(String(50), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IntegrationSyncStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, integration_id: UUID, resource: str) -> IntegrationSyncStateORM | None:
        return await self._session.get(IntegrationSyncStateORM, (integration_id, resource))

    async def list_all(self) -> Sequence[IntegrationSyncStateORM]:
        """All checkpoint rows across every integration/resource — the table is
        one row per (integration_id, resource), small enough to fetch whole for
        the dashboard's sync-status view rather than adding pagination here."""
        stmt = select(IntegrationSyncStateORM).order_by(IntegrationSyncStateORM.updated_at.desc())
        return (await self._session.scalars(stmt)).all()

    async def save_cursor(
        self, integration_id: UUID, resource: str, cursor: str | None, status: str
    ) -> IntegrationSyncStateORM:
        state = await self.get(integration_id, resource)
        if state is None:
            state = IntegrationSyncStateORM(integration_id=integration_id, resource=resource)
            self._session.add(state)
        state.cursor = cursor
        state.status = status
        state.last_synced_at = datetime.now(UTC)
        await self._session.flush()
        return state
