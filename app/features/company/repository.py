"""Data access for companies.

Receives a request-scoped `AsyncSession` (see `get_session`) and never
commits/rollbacks itself — the session dependency owns the transaction.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.company.orm import CompanyORM
from app.features.company.schemas import CompanyCreate, CompanyUpdate


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: CompanyCreate) -> CompanyORM:
        company = CompanyORM(**data.model_dump())
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def get(self, company_id: UUID) -> CompanyORM | None:
        return await self._session.get(CompanyORM, company_id)

    async def list(self, limit: int = 100, offset: int = 0) -> Sequence[CompanyORM]:
        stmt = select(CompanyORM).order_by(CompanyORM.created_at.desc()).limit(limit).offset(offset)
        return (await self._session.scalars(stmt)).all()

    async def update(self, company_id: UUID, data: CompanyUpdate) -> CompanyORM | None:
        company = await self.get(company_id)
        if company is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def delete(self, company_id: UUID) -> bool:
        company = await self.get(company_id)
        if company is None:
            return False
        await self._session.delete(company)
        await self._session.flush()
        return True
