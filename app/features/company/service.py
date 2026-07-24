"""Business logic layer.

The router depends on `CompanyService`, never on `CompanyRepository`
directly. Uniqueness/existence rules are validated explicitly here, by
querying first — the application must never rely on catching a database
constraint violation to enforce a business rule. DB constraints stay in
place as a last-resort safety net (e.g. against races), not as the
validation mechanism.
"""

from collections.abc import Sequence
from uuid import UUID

from app.features.company.orm import CompanyORM
from app.features.company.repository import CompanyRepository
from app.features.company.schemas import CompanyCreate, CompanyUpdate


class CompanyAlreadyExistsError(Exception):
    """Raised when `external_company_id` already belongs to another company."""


class CompanyService:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    async def create(self, data: CompanyCreate) -> CompanyORM:
        existing = await self._repository.get_by_external_company_id(data.external_company_id)
        if existing is not None:
            raise CompanyAlreadyExistsError
        return await self._repository.create(data)

    async def get(self, company_id: UUID) -> CompanyORM | None:
        return await self._repository.get(company_id)

    async def list(self, limit: int = 100, offset: int = 0) -> Sequence[CompanyORM]:
        return await self._repository.list(limit=limit, offset=offset)

    async def update(self, company_id: UUID, data: CompanyUpdate) -> CompanyORM | None:
        company = await self._repository.get(company_id)
        if company is None:
            return None
        if (
            data.external_company_id is not None
            and data.external_company_id != company.external_company_id
        ):
            existing = await self._repository.get_by_external_company_id(data.external_company_id)
            if existing is not None:
                raise CompanyAlreadyExistsError
        return await self._repository.update(company_id, data)

    async def delete(self, company_id: UUID) -> bool:
        return await self._repository.delete(company_id)
