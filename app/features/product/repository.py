"""Data access for products synced directly from ERP product endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.integration.orm import IntegrationORM
from app.features.product.orm import ProductORM

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, _DATETIME_FORMAT)


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(
        self, integration_id: UUID, external_company_id: UUID, products: list[dict[str, Any]]
    ) -> int:
        if not products:
            return 0

        rows = [
            {
                "id": uuid4(),
                "integration_id": integration_id,
                "external_product_id": str(product["id"]),
                "external_company_id": external_company_id,
                "integration_product_id": product.get("integration_id"),
                "code": product.get("code"),
                "name": product.get("name"),
                "description": product.get("description"),
                "full_description": product.get("full_description"),
                "composition": product.get("composition"),
                "active": bool(product.get("active", True)),
                "price": _float_or_none(product.get("price")),
                "promotion": bool(product.get("promotion", False)),
                "price_promotional": _float_or_none(product.get("price_promotional")),
                "slug": product.get("slug"),
                "url": product.get("url"),
                "weight": _float_or_none(product.get("weight")),
                "height": _float_or_none(product.get("height")),
                "width": _float_or_none(product.get("width")),
                "length": _float_or_none(product.get("length")),
                "external_created_at": _parse_dt(product.get("created_at")),
                "external_updated_at": _parse_dt(product.get("updated_at")),
                "release_at": _parse_dt(product.get("release_at")),
                "order_date": _parse_dt(product.get("order_date")),
                "brand": product.get("brand") or {},
                "categories": product.get("categories") or [],
                "negotiations": product.get("negotiations") or [],
                "sizes": product.get("sizes") or [],
                "colors": product.get("colors") or [],
                "stocks": product.get("stocks") or [],
                "media": product.get("media") or [],
            }
            for product in products
        ]
        stmt = pg_insert(ProductORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_products_integration_external_id",
            set_={
                "external_company_id": stmt.excluded.external_company_id,
                "integration_product_id": stmt.excluded.integration_product_id,
                "code": stmt.excluded.code,
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "full_description": stmt.excluded.full_description,
                "composition": stmt.excluded.composition,
                "active": stmt.excluded.active,
                "price": stmt.excluded.price,
                "promotion": stmt.excluded.promotion,
                "price_promotional": stmt.excluded.price_promotional,
                "slug": stmt.excluded.slug,
                "url": stmt.excluded.url,
                "weight": stmt.excluded.weight,
                "height": stmt.excluded.height,
                "width": stmt.excluded.width,
                "length": stmt.excluded.length,
                "external_created_at": stmt.excluded.external_created_at,
                "external_updated_at": stmt.excluded.external_updated_at,
                "release_at": stmt.excluded.release_at,
                "order_date": stmt.excluded.order_date,
                "brand": stmt.excluded.brand,
                "categories": stmt.excluded.categories,
                "negotiations": stmt.excluded.negotiations,
                "sizes": stmt.excluded.sizes,
                "colors": stmt.excluded.colors,
                "stocks": stmt.excluded.stocks,
                "media": stmt.excluded.media,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(rows)

    async def get_for_company(self, product_id: UUID, company_id: UUID) -> ProductORM | None:
        stmt = (
            select(ProductORM)
            .join(IntegrationORM, IntegrationORM.id == ProductORM.integration_id)
            .where(ProductORM.id == product_id, IntegrationORM.company_id == company_id)
        )
        return await self._session.scalar(stmt)

    async def list_for_company(
        self,
        company_id: UUID,
        search: str | None = None,
        integration_id: UUID | None = None,
        active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[ProductORM], int]:
        stmt = (
            select(ProductORM)
            .join(IntegrationORM, IntegrationORM.id == ProductORM.integration_id)
            .where(IntegrationORM.company_id == company_id)
        )
        total_stmt = (
            select(func.count(ProductORM.id))
            .join(IntegrationORM, IntegrationORM.id == ProductORM.integration_id)
            .where(IntegrationORM.company_id == company_id)
        )

        filters = []
        if integration_id is not None:
            filters.append(ProductORM.integration_id == integration_id)
        if active is not None:
            filters.append(ProductORM.active.is_(active))
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    ProductORM.name.ilike(pattern),
                    ProductORM.code.ilike(pattern),
                    ProductORM.integration_product_id.ilike(pattern),
                )
            )
        if filters:
            stmt = stmt.where(*filters)
            total_stmt = total_stmt.where(*filters)

        total = int(await self._session.scalar(total_stmt) or 0)
        stmt = (
            stmt.order_by(
                ProductORM.external_updated_at.desc().nulls_last(),
                ProductORM.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.scalars(stmt)).all(), total
