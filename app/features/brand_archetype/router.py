from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.brand_archetype.schemas import (
    BrandArchetypeProfileCreate,
    BrandArchetypeProfileResponse,
    BrandArchetypeProfileUpdate,
)
from app.features.brand_archetype.service import (
    BrandArchetypeProfileAlreadyExistsError,
    BrandArchetypeProfileService,
    CompanyNotFoundError,
)
from app.features.company.repository import CompanyRepository
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/brand-archetype-profiles", tags=["brand-archetype-profiles"])


def get_brand_archetype_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BrandArchetypeProfileService:
    return BrandArchetypeProfileService(
        BrandArchetypeProfileRepository(session), CompanyRepository(session)
    )


ServiceDep = Annotated[BrandArchetypeProfileService, Depends(get_brand_archetype_profile_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("", response_model=BrandArchetypeProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_archetype_profile(
    data: BrandArchetypeProfileCreate, service: ServiceDep, current_user: CurrentUserDep
) -> BrandArchetypeProfileResponse:
    if data.company_id != current_user.company_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Cannot create a profile for another company"
        )
    try:
        profile = await service.create(data)
    except CompanyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found") from exc
    except BrandArchetypeProfileAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This company already has a brand archetype profile",
        ) from exc
    return BrandArchetypeProfileResponse.model_validate(profile)


@router.get("", response_model=list[BrandArchetypeProfileResponse])
async def list_brand_archetype_profiles(
    service: ServiceDep, current_user: CurrentUserDep
) -> list[BrandArchetypeProfileResponse]:
    profile = await service.get_by_company_id(current_user.company_id)
    return [BrandArchetypeProfileResponse.model_validate(profile)] if profile is not None else []


@router.get("/{profile_id}", response_model=BrandArchetypeProfileResponse)
async def get_brand_archetype_profile(
    profile_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> BrandArchetypeProfileResponse:
    profile = await service.get_for_company(profile_id, current_user.company_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand archetype profile not found")
    return BrandArchetypeProfileResponse.model_validate(profile)


@router.patch("/{profile_id}", response_model=BrandArchetypeProfileResponse)
async def update_brand_archetype_profile(
    profile_id: UUID,
    data: BrandArchetypeProfileUpdate,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> BrandArchetypeProfileResponse:
    existing = await service.get_for_company(profile_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand archetype profile not found")
    profile = await service.update(profile_id, data)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand archetype profile not found")
    return BrandArchetypeProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_archetype_profile(
    profile_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> None:
    existing = await service.get_for_company(profile_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand archetype profile not found")
    await service.delete(profile_id)
