from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.company.repository import CompanyRepository
from app.features.company.schemas import CompanyCreate, CompanyResponse, CompanyUpdate
from app.features.company.service import CompanyAlreadyExistsError, CompanyService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CompanyService:
    return CompanyService(CompanyRepository(session))


ServiceDep = Annotated[CompanyService, Depends(get_company_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(data: CompanyCreate, service: ServiceDep) -> CompanyResponse:
    try:
        company = await service.create(data)
    except CompanyAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A company with this external_company_id already exists",
        ) from exc
    return CompanyResponse.model_validate(company)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    service: ServiceDep, current_user: CurrentUserDep, limit: int = 100, offset: int = 0
) -> list[CompanyResponse]:
    company = await service.get(current_user.company_id)
    return [CompanyResponse.model_validate(company)] if company is not None else []


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> CompanyResponse:
    if company_id != current_user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    company = await service.get(company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return CompanyResponse.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID, data: CompanyUpdate, service: ServiceDep, current_user: CurrentUserDep
) -> CompanyResponse:
    if company_id != current_user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    try:
        company = await service.update(company_id, data)
    except CompanyAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A company with this external_company_id already exists",
        ) from exc
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> None:
    if company_id != current_user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    deleted = await service.delete(company_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
