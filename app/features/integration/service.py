"""Business logic layer.

The router depends on `IntegrationService` only, never on
`IntegrationRepository` directly. Every rule (the company must exist, the
provider must not be duplicated for that company) is validated explicitly
here by querying first — the application must never rely on catching a
database constraint violation (unique/foreign key) to enforce a business
rule. DB constraints stay in place as a last-resort safety net, not as the
validation mechanism.
"""

from collections.abc import Sequence
from uuid import UUID

from app.features.company.repository import CompanyRepository
from app.features.integration.orm import IntegrationORM
from app.features.integration.repository import IntegrationRepository
from app.features.integration.schemas import IntegrationCreate, IntegrationUpdate


class IntegrationAlreadyExistsError(Exception):
    """Raised when the company already has an integration for this provider."""


class CompanyNotFoundError(Exception):
    """Raised when `company_id` does not reference an existing company."""


class IntegrationService:
    def __init__(
        self, repository: IntegrationRepository, company_repository: CompanyRepository
    ) -> None:
        self._repository = repository
        self._company_repository = company_repository

    async def create(self, data: IntegrationCreate) -> IntegrationORM:
        company = await self._company_repository.get(data.company_id)
        if company is None:
            raise CompanyNotFoundError

        existing = await self._repository.get_by_company_and_provider(
            data.company_id, data.provider.value
        )
        if existing is not None:
            raise IntegrationAlreadyExistsError

        return await self._repository.create(data)

    async def get(self, integration_id: UUID) -> IntegrationORM | None:
        return await self._repository.get(integration_id)

    async def get_for_company(
        self, integration_id: UUID, company_id: UUID
    ) -> IntegrationORM | None:
        return await self._repository.get_for_company(integration_id, company_id)

    async def list(
        self, company_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[IntegrationORM]:
        return await self._repository.list(company_id=company_id, limit=limit, offset=offset)

    async def update(self, integration_id: UUID, data: IntegrationUpdate) -> IntegrationORM | None:
        return await self._repository.update(integration_id, data)

    async def delete(self, integration_id: UUID) -> bool:
        return await self._repository.delete(integration_id)
