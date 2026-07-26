from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    external_product_id: str
    external_company_id: UUID
    integration_product_id: str | None
    code: str | None
    name: str | None
    description: str | None
    full_description: str | None
    composition: str | None
    active: bool
    price: float | None
    promotion: bool
    price_promotional: float | None
    slug: str | None
    url: str | None
    weight: float | None
    height: float | None
    width: float | None
    length: float | None
    external_created_at: datetime | None
    external_updated_at: datetime | None
    release_at: datetime | None
    order_date: datetime | None
    brand: dict[str, Any]
    categories: list[dict[str, Any]]
    negotiations: list[dict[str, Any]]
    sizes: list[dict[str, Any]]
    colors: list[dict[str, Any]]
    stocks: list[dict[str, Any]]
    media: list[dict[str, Any]]
    image_url: str | None
    image_fallback_url: str | None
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
