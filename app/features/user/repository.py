"""Data access for users."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.user.orm import UserORM
from app.features.user.schemas import UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        company_id: UUID,
        email: str,
        name: str,
        password_hash: str,
        role: str,
        is_active: bool,
    ) -> UserORM:
        user = UserORM(
            company_id=company_id,
            email=email.lower(),
            name=name,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get(self, user_id: UUID) -> UserORM | None:
        return await self._session.get(UserORM, user_id)

    async def get_by_email(self, email: str) -> UserORM | None:
        stmt = select(UserORM).where(UserORM.email == email.lower())
        return await self._session.scalar(stmt)

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[UserORM]:
        stmt = (
            select(UserORM)
            .where(UserORM.company_id == company_id)
            .order_by(UserORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.scalars(stmt)).all()

    async def update(self, user_id: UUID, data: UserUpdate) -> UserORM | None:
        user = await self.get(user_id)
        if user is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value.value if hasattr(value, "value") else value)
        await self._session.flush()
        await self._session.refresh(user)
        return user
