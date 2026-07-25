"""Persistence for Oráculo chat sessions and messages."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.rag.chat_orm import ChatMessageORM, ChatSessionORM


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, company_id: UUID, user_id: UUID, title: str) -> ChatSessionORM:
        chat_session = ChatSessionORM(company_id=company_id, user_id=user_id, title=title)
        self._session.add(chat_session)
        await self._session.flush()
        await self._session.refresh(chat_session)
        return chat_session

    async def list_sessions(
        self, company_id: UUID, user_id: UUID, limit: int = 30
    ) -> Sequence[ChatSessionORM]:
        stmt = (
            select(ChatSessionORM)
            .where(ChatSessionORM.company_id == company_id, ChatSessionORM.user_id == user_id)
            .order_by(ChatSessionORM.updated_at.desc())
            .limit(limit)
        )
        return (await self._session.scalars(stmt)).all()

    async def get_session(
        self, session_id: UUID, company_id: UUID, user_id: UUID
    ) -> ChatSessionORM | None:
        stmt = select(ChatSessionORM).where(
            ChatSessionORM.id == session_id,
            ChatSessionORM.company_id == company_id,
            ChatSessionORM.user_id == user_id,
        )
        return await self._session.scalar(stmt)

    async def touch_session(self, session_id: UUID) -> None:
        await self._session.execute(
            update(ChatSessionORM)
            .where(ChatSessionORM.id == session_id)
            .values(updated_at=func.now())
        )

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        route: str | None = None,
        generated_query: str | None = None,
        sources: list | None = None,
    ) -> ChatMessageORM:
        message = ChatMessageORM(
            session_id=session_id,
            role=role,
            content=content,
            route=route,
            generated_query=generated_query,
            sources=sources,
        )
        self._session.add(message)
        await self.touch_session(session_id)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    async def list_messages(self, session_id: UUID, limit: int = 80) -> Sequence[ChatMessageORM]:
        stmt = (
            select(ChatMessageORM)
            .where(ChatMessageORM.session_id == session_id)
            .order_by(ChatMessageORM.created_at.asc())
            .limit(limit)
        )
        return (await self._session.scalars(stmt)).all()

    async def recent_messages(self, session_id: UUID, limit: int = 12) -> Sequence[ChatMessageORM]:
        stmt = (
            select(ChatMessageORM)
            .where(ChatMessageORM.session_id == session_id)
            .order_by(ChatMessageORM.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.scalars(stmt)).all()
        return list(reversed(rows))
