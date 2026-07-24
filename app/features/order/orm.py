"""ORM model for orders pulled from an ERP via an integration.

Scalar/queryable fields from the ERP's order document get real columns;
nested objects/arrays (`customer`, `products`, `address`, `freight`,
`seller`, `payment`, `summary`) stay as JSONB, since their shape is owned by
the ERP and not something we query into directly today. `payload` keeps the
*entire* raw response alongside the structured columns — a safety net in
case a given order carries fields we haven't modeled (different ERPs/order
types don't all return the same top-level keys; e.g. Vesti's `status`,
`unification`, `general_status` show up on some orders but not others).

`external_created_at`/`external_updated_at`/`expires_at` are stored
timezone-naive: the ERP sends bare `"YYYY-MM-DD HH:MM:SS"` strings with no
offset, and we don't yet know for certain which timezone that is — storing
naive avoids silently asserting a UTC offset that might be wrong. `created_at`/
`updated_at` (no `external_` prefix) are our own row bookkeeping, always UTC.

`external_order_id` is the ERP's own order id (e.g. Vesti's Mongo-style id),
unique per integration so re-syncing the same order updates it in place
instead of duplicating it.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class OrderORM(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint(
            "integration_id", "external_order_id", name="uq_orders_integration_external_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE", name="fk_orders_integration_id"),
        nullable=False,
    )

    external_order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_company_id: Mapped[UUID] = mapped_column(nullable=False)
    code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observations: Mapped[str | None] = mapped_column(nullable=True)

    external_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    external_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    customer: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    products: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    freight: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    seller: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    payment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
