"""Business logic layer.

The router depends on `CompanyService`, never on `CompanyRepository` directly
— persistence details (e.g. a unique-constraint violation) are translated
here into domain-level exceptions the router can map to HTTP responses.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.company.orm import CompanyORM
from app.features.company.repository import CompanyRepository
from app.features.company.schemas import CompanyCreate, CompanyUpdate


class CompanyAlreadyExistsError(Exception):
    """Raised when `external_company_id` already belongs to another company."""


class CompanyService:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    async def create(self, data: CompanyCreate) -> CompanyORM:
        try:
            return await self._repository.create(data)
        except IntegrityError as exc:
            raise CompanyAlreadyExistsError from exc

    async def get(self, company_id: UUID) -> CompanyORM | None:
        return await self._repository.get(company_id)

    async def list(self, limit: int = 100, offset: int = 0) -> Sequence[CompanyORM]:
        return await self._repository.list(limit=limit, offset=offset)

    async def update(self, company_id: UUID, data: CompanyUpdate) -> CompanyORM | None:
        try:
            return await self._repository.update(company_id, data)
        except IntegrityError as exc:
            raise CompanyAlreadyExistsError from exc

    async def delete(self, company_id: UUID) -> bool:
        return await self._repository.delete(company_id)
