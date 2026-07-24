from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.company.repository import CompanyRepository
from app.features.integration.repository import IntegrationRepository
from app.features.integration.schemas import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
)
from app.features.integration.service import (
    CompanyNotFoundError,
    IntegrationAlreadyExistsError,
    IntegrationService,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_integration_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IntegrationService:
    return IntegrationService(IntegrationRepository(session), CompanyRepository(session))


ServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(data: IntegrationCreate, service: ServiceDep) -> IntegrationResponse:
    try:
        integration = await service.create(data)
    except IntegrationAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This company already has an integration registered for this provider",
        ) from exc
    except CompanyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found") from exc
    return IntegrationResponse.model_validate(integration)


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    service: ServiceDep,
    company_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[IntegrationResponse]:
    integrations = await service.list(company_id=company_id, limit=limit, offset=offset)
    return [IntegrationResponse.model_validate(integration) for integration in integrations]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(integration_id: UUID, service: ServiceDep) -> IntegrationResponse:
    integration = await service.get(integration_id)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID, data: IntegrationUpdate, service: ServiceDep
) -> IntegrationResponse:
    integration = await service.update(integration_id, data)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(integration_id: UUID, service: ServiceDep) -> None:
    deleted = await service.delete(integration_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
