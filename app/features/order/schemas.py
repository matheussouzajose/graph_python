from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    external_order_id: str
    external_company_id: UUID
    code: int | None
    origin: str | None
    observations: str | None
    external_created_at: datetime | None
    external_updated_at: datetime | None
    expires_at: datetime | None
    customer: dict[str, Any]
    products: list[dict[str, Any]]
    address: dict[str, Any]
    freight: dict[str, Any]
    seller: dict[str, Any]
    payment: dict[str, Any]
    summary: dict[str, Any]
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
