"""ORM model for products pulled directly from an ERP integration."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class ProductORM(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "integration_id", "external_product_id", name="uq_products_integration_external_id"
        ),
        Index("ix_products_integration_updated_at", "integration_id", "external_updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE", name="fk_products_integration_id"),
        nullable=False,
    )

    external_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_company_id: Mapped[UUID] = mapped_column(nullable=False)
    integration_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    full_description: Mapped[str | None] = mapped_column(nullable=True)
    composition: Mapped[str | None] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    promotion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price_promotional: Mapped[float | None] = mapped_column(Float, nullable=True)
    slug: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    length: Mapped[float | None] = mapped_column(Float, nullable=True)

    external_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    external_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    order_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    brand: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    categories: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    negotiations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    sizes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    colors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    stocks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    media: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
