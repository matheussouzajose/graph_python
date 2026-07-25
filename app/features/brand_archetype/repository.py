"""Data access for brand archetype profiles.

Receives a request-scoped `AsyncSession` (see `get_session`) and never
commits/rollbacks itself — the session dependency owns the transaction.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.brand_archetype.orm import BrandArchetypeProfileORM
from app.features.brand_archetype.schemas import (
    BrandArchetypeProfileCreate,
    BrandArchetypeProfileUpdate,
)


class BrandArchetypeProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: BrandArchetypeProfileCreate) -> BrandArchetypeProfileORM:
        profile = BrandArchetypeProfileORM(
            company_id=data.company_id,
            primary_archetype=data.primary_archetype.value,
            secondary_archetype=(
                data.secondary_archetype.value if data.secondary_archetype else None
            ),
            archetype_scores=data.archetype_scores,
            core_desire=data.core_desire,
            fear=data.fear,
            strategy=data.strategy,
            voice=data.voice.model_dump(),
            audience=data.audience.model_dump(),
            messaging_pillars=data.messaging_pillars,
            guardrails=data.guardrails.model_dump(),
            reference_examples=data.reference_examples,
        )
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile

    async def get(self, profile_id: UUID) -> BrandArchetypeProfileORM | None:
        return await self._session.get(BrandArchetypeProfileORM, profile_id)

    async def get_for_company(
        self, profile_id: UUID, company_id: UUID
    ) -> BrandArchetypeProfileORM | None:
        stmt = select(BrandArchetypeProfileORM).where(
            BrandArchetypeProfileORM.id == profile_id,
            BrandArchetypeProfileORM.company_id == company_id,
        )
        return await self._session.scalar(stmt)

    async def get_by_company_id(self, company_id: UUID) -> BrandArchetypeProfileORM | None:
        stmt = select(BrandArchetypeProfileORM).where(
            BrandArchetypeProfileORM.company_id == company_id
        )
        return await self._session.scalar(stmt)

    async def update(
        self, profile_id: UUID, data: BrandArchetypeProfileUpdate
    ) -> BrandArchetypeProfileORM | None:
        profile = await self.get(profile_id)
        if profile is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile

    async def delete(self, profile_id: UUID) -> bool:
        profile = await self.get(profile_id)
        if profile is None:
            return False
        await self._session.delete(profile)
        await self._session.flush()
        return True
