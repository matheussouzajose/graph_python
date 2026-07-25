"""Business logic layer.

The router depends on `BrandArchetypeProfileService` only, never on
`BrandArchetypeProfileRepository` directly. Every rule (the company must
exist, a company may have at most one profile) is validated explicitly here
by querying first — the application must never rely on catching a database
constraint violation (unique/foreign key) to enforce a business rule. DB
constraints stay in place as a last-resort safety net, not as the validation
mechanism.
"""

from uuid import UUID

from app.features.brand_archetype.orm import BrandArchetypeProfileORM
from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.brand_archetype.schemas import (
    BrandArchetypeProfileCreate,
    BrandArchetypeProfileUpdate,
)
from app.features.company.repository import CompanyRepository


class CompanyNotFoundError(Exception):
    """Raised when `company_id` does not reference an existing company."""


class BrandArchetypeProfileAlreadyExistsError(Exception):
    """Raised when the company already has a brand archetype profile."""


class BrandArchetypeProfileService:
    def __init__(
        self,
        repository: BrandArchetypeProfileRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self._repository = repository
        self._company_repository = company_repository

    async def create(self, data: BrandArchetypeProfileCreate) -> BrandArchetypeProfileORM:
        company = await self._company_repository.get(data.company_id)
        if company is None:
            raise CompanyNotFoundError

        existing = await self._repository.get_by_company_id(data.company_id)
        if existing is not None:
            raise BrandArchetypeProfileAlreadyExistsError

        return await self._repository.create(data)

    async def get(self, profile_id: UUID) -> BrandArchetypeProfileORM | None:
        return await self._repository.get(profile_id)

    async def get_for_company(
        self, profile_id: UUID, company_id: UUID
    ) -> BrandArchetypeProfileORM | None:
        return await self._repository.get_for_company(profile_id, company_id)

    async def get_by_company_id(self, company_id: UUID) -> BrandArchetypeProfileORM | None:
        return await self._repository.get_by_company_id(company_id)

    async def update(
        self, profile_id: UUID, data: BrandArchetypeProfileUpdate
    ) -> BrandArchetypeProfileORM | None:
        return await self._repository.update(profile_id, data)

    async def delete(self, profile_id: UUID) -> bool:
        return await self._repository.delete(profile_id)
