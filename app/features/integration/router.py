from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.core.infrastructure.messaging.base import Event
from app.core.infrastructure.messaging.client import get_integration_event_producer
from app.core.infrastructure.messaging.events import INTEGRATION_SYNC_REQUESTED
from app.features.company.repository import CompanyRepository
from app.features.integration.repository import IntegrationRepository
from app.features.integration.schemas import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
    SyncTriggerResponse,
)
from app.features.integration.service import (
    CompanyNotFoundError,
    IntegrationAlreadyExistsError,
    IntegrationService,
)
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_integration_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IntegrationService:
    return IntegrationService(IntegrationRepository(session), CompanyRepository(session))


ServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    data: IntegrationCreate, service: ServiceDep, current_user: CurrentUserDep
) -> IntegrationResponse:
    if data.company_id != current_user.company_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Cannot create integration for another company"
        )
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
    current_user: CurrentUserDep,
    company_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[IntegrationResponse]:
    if company_id is not None and company_id != current_user.company_id:
        return []
    company_id = current_user.company_id
    integrations = await service.list(company_id=company_id, limit=limit, offset=offset)
    return [IntegrationResponse.model_validate(integration) for integration in integrations]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> IntegrationResponse:
    integration = await service.get_for_company(integration_id, current_user.company_id)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    data: IntegrationUpdate,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> IntegrationResponse:
    existing = await service.get_for_company(integration_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    integration = await service.update(integration_id, data)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> None:
    existing = await service.get_for_company(integration_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    deleted = await service.delete(integration_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")


@router.post(
    "/{integration_id}/sync",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_integration_sync(
    integration_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> SyncTriggerResponse:
    """Publishes a sync request to Redis and returns immediately.

    Durable and decoupled from this process: unlike an in-process background
    task, the trigger survives an API restart/redeploy between the request
    and the moment `order/sync_consumer.py` actually picks it up and calls
    `run_order_sync`. Progress is checkpointed per page regardless of who
    ends up running it (this trigger or `OrderSyncWorker`'s periodic poll),
    so re-triggering mid-run just resumes from the last saved cursor.
    """
    integration = await service.get_for_company(integration_id, current_user.company_id)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")

    producer = get_integration_event_producer()
    await producer.publish(
        Event(
            name=INTEGRATION_SYNC_REQUESTED,
            payload={"integration_id": str(integration_id)},
        )
    )
    return SyncTriggerResponse(status="accepted", integration_id=integration_id)
