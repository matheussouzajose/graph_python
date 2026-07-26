"""Data access for agent execution history.

Receives a request-scoped `AsyncSession` (see `get_session`) and never
commits/rollbacks itself — the session dependency owns the transaction.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agents.run_orm import AgentRunORM


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, agent_id: UUID, company_id: UUID, input_data: dict[str, Any]
    ) -> AgentRunORM:
        run = AgentRunORM(
            agent_id=agent_id, company_id=company_id, input=input_data, status="pending"
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get(self, run_id: UUID) -> AgentRunORM | None:
        return await self._session.get(AgentRunORM, run_id)

    async def get_for_company(self, run_id: UUID, company_id: UUID) -> AgentRunORM | None:
        stmt = select(AgentRunORM).where(
            AgentRunORM.id == run_id, AgentRunORM.company_id == company_id
        )
        return await self._session.scalar(stmt)

    async def list_for_company(
        self,
        company_id: UUID,
        agent_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AgentRunORM]:
        stmt = (
            select(AgentRunORM)
            .where(AgentRunORM.company_id == company_id)
            .order_by(AgentRunORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if agent_id is not None:
            stmt = stmt.where(AgentRunORM.agent_id == agent_id)
        return (await self._session.scalars(stmt)).all()

    async def list_running_video_jobs(self) -> Sequence[AgentRunORM]:
        """Used by `video_worker.py` to find runs waiting on a Sora job."""
        stmt = select(AgentRunORM).where(
            AgentRunORM.status == "running", AgentRunORM.external_job_id.is_not(None)
        )
        return (await self._session.scalars(stmt)).all()

    async def mark_running(self, run: AgentRunORM, external_job_id: str) -> AgentRunORM:
        run.status = "running"
        run.external_job_id = external_job_id
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def update_output_text(self, run: AgentRunORM, text: str) -> AgentRunORM:
        output = dict(run.output or {})
        output["text"] = text
        run.output = output
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def mark_completed(self, run: AgentRunORM, output: dict[str, Any]) -> AgentRunORM:
        run.status = "completed"
        run.output = output
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def mark_failed(self, run: AgentRunORM, error: str) -> AgentRunORM:
        run.status = "failed"
        run.error = error
        await self._session.flush()
        await self._session.refresh(run)
        return run
