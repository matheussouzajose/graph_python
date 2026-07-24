from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntegrationProvider(StrEnum):
    """Known ERP/integration providers.

    Stored as plain text in the DB (see `IntegrationORM.provider`) — add a
    member here when onboarding a new ERP, no migration required.
    """

    VESTI = "vesti"


class IntegrationCreate(BaseModel):
    company_id: UUID
    provider: IntegrationProvider
    name: str
    base_url: str
    configs: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class IntegrationUpdate(BaseModel):
    """`company_id` and `provider` are intentionally not editable — moving an
    integration to another company/provider means deleting and recreating it.
    """

    name: str | None = None
    base_url: str | None = None
    configs: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    is_active: bool | None = None


class SyncTriggerResponse(BaseModel):
    status: str
    integration_id: UUID


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    provider: str
    name: str
    base_url: str
    configs: dict[str, Any]
    params: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
