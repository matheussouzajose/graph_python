"""Data access for agent definitions.

Receives a request-scoped `AsyncSession` (see `get_session`) and never
commits/rollbacks itself — the session dependency owns the transaction.

Two distinct query scopes, deliberately not shared:
- "owned" (`get_owned_by_company`) — strict `company_id` match. Used to
  authorize update/delete: only the owner can mutate an agent, global or not.
- "visible" (`get_visible_to_company`/`list_visible_to_company`) — owned OR
  `is_global`. Used for read/run: a company can see and execute its own
  agents plus every global one, but never edit someone else's.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agents.orm import AgentORM
from app.features.agents.schemas import AgentCreate, AgentUpdate


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: AgentCreate) -> AgentORM:
        agent = AgentORM(
            company_id=data.company_id,
            name=data.name,
            description=data.description,
            kind=data.kind.value,
            usage_instructions=data.usage_instructions,
            system_prompt=data.system_prompt,
            model=data.model,
            temperature=data.temperature,
            uses_brand_archetype=data.uses_brand_archetype,
            response_format=data.response_format.value,
            output_action=data.output_action.value,
            video_provider=data.video_provider.value,
            video_size=data.video_size,
            video_seconds=data.video_seconds,
            is_active=data.is_active,
            is_global=data.is_global,
        )
        self._session.add(agent)
        await self._session.flush()
        await self._session.refresh(agent)
        return agent

    async def get(self, agent_id: UUID) -> AgentORM | None:
        return await self._session.get(AgentORM, agent_id)

    async def get_owned_by_company(self, agent_id: UUID, company_id: UUID) -> AgentORM | None:
        stmt = select(AgentORM).where(AgentORM.id == agent_id, AgentORM.company_id == company_id)
        return await self._session.scalar(stmt)

    async def get_visible_to_company(self, agent_id: UUID, company_id: UUID) -> AgentORM | None:
        stmt = select(AgentORM).where(
            AgentORM.id == agent_id,
            or_(AgentORM.company_id == company_id, AgentORM.is_global.is_(True)),
        )
        return await self._session.scalar(stmt)

    async def list_visible_to_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[AgentORM]:
        stmt = (
            select(AgentORM)
            .where(or_(AgentORM.company_id == company_id, AgentORM.is_global.is_(True)))
            .order_by(AgentORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.scalars(stmt)).all()

    async def update(self, agent_id: UUID, data: AgentUpdate) -> AgentORM | None:
        agent = await self.get(agent_id)
        if agent is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(agent, field, value)
        await self._session.flush()
        await self._session.refresh(agent)
        return agent

    async def delete(self, agent_id: UUID) -> bool:
        agent = await self.get(agent_id)
        if agent is None:
            return False
        await self._session.delete(agent)
        await self._session.flush()
        return True
