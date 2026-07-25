"""Data access for integrations.

Receives a request-scoped `AsyncSession` (see `get_session`) and never
commits/rollbacks itself — the session dependency owns the transaction.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.integration.orm import IntegrationORM
from app.features.integration.schemas import IntegrationCreate, IntegrationUpdate


class IntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: IntegrationCreate) -> IntegrationORM:
        integration = IntegrationORM(
            company_id=data.company_id,
            provider=data.provider.value,
            name=data.name,
            base_url=data.base_url,
            configs=data.configs,
            params=data.params,
            is_active=data.is_active,
        )
        self._session.add(integration)
        await self._session.flush()
        await self._session.refresh(integration)
        return integration

    async def get(self, integration_id: UUID) -> IntegrationORM | None:
        return await self._session.get(IntegrationORM, integration_id)

    async def get_for_company(
        self, integration_id: UUID, company_id: UUID
    ) -> IntegrationORM | None:
        stmt = select(IntegrationORM).where(
            IntegrationORM.id == integration_id,
            IntegrationORM.company_id == company_id,
        )
        return await self._session.scalar(stmt)

    async def get_by_company_and_provider(
        self, company_id: UUID, provider: str
    ) -> IntegrationORM | None:
        stmt = select(IntegrationORM).where(
            IntegrationORM.company_id == company_id,
            IntegrationORM.provider == provider,
        )
        return await self._session.scalar(stmt)

    async def list(
        self, company_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[IntegrationORM]:
        stmt = (
            select(IntegrationORM)
            .order_by(IntegrationORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if company_id is not None:
            stmt = stmt.where(IntegrationORM.company_id == company_id)
        return (await self._session.scalars(stmt)).all()

    async def list_active(self) -> Sequence[IntegrationORM]:
        stmt = select(IntegrationORM).where(IntegrationORM.is_active.is_(True))
        return (await self._session.scalars(stmt)).all()

    async def update(self, integration_id: UUID, data: IntegrationUpdate) -> IntegrationORM | None:
        integration = await self.get(integration_id)
        if integration is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(integration, field, value)
        await self._session.flush()
        await self._session.refresh(integration)
        return integration

    async def delete(self, integration_id: UUID) -> bool:
        integration = await self.get(integration_id)
        if integration is None:
            return False
        await self._session.delete(integration)
        await self._session.flush()
        return True
