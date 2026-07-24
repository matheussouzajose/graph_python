from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    domain_id: int
    external_company_id: UUID
    is_active: bool = True


class CompanyUpdate(BaseModel):
    name: str | None = None
    domain_id: int | None = None
    external_company_id: UUID | None = None
    is_active: bool | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    domain_id: int
    external_company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
