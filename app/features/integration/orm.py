"""ORM model for ERP/third-party integrations belonging to a company.

`configs` holds credentials/secrets, `params` holds non-secret behavioral
settings (sync frequency, warehouse id, ...) — kept as two separate JSONB
columns so the two can be masked/handled differently (see
`observability/masking.py`, which redacts `configs` wholesale in logs).
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class IntegrationORM(Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", name="uq_integrations_company_provider"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_integrations_company_id"),
        nullable=False,
    )
    # Which ERP/system this integration talks to (e.g. "vesti"). Plain text,
    # not a DB enum — see `IntegrationProvider` in schemas.py for the
    # application-level allow-list; adding a provider is a code change, not
    # a migration.
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    configs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
