"""Async database engine, session factory and the per-request session
dependency.

Three levels, from long-lived to short-lived:

    engine              -> created once, holds the connection pool
    AsyncSessionFactory -> created once, mints sessions
    get_session()       -> one AsyncSession PER REQUEST (unit of work)

`get_session` is a FastAPI dependency: it opens a session, hands it to
the request, then commits on success or rolls back on error and always
closes it. Repositories receive this session and never manage
transactions themselves.
"""
from collections.abc import AsyncIterator

import psycopg
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# One engine for the whole process. create_async_engine is lazy — it does
# NOT open a connection here, only when the first query runs.
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.IS_DEBUG,   # logs SQL when debugging
    pool_pre_ping=True,       # drops dead connections instead of failing
)

AsyncSessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,   # keep attributes usable after commit
    autoflush=False,
)

async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session (unit of work).

    Commits if the request succeeded, rolls back on any exception, and
    closes the session either way.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_connection() -> psycopg.Connection:
    """Plain sync psycopg connection, for raw SQL outside the SQLAlchemy engine
    (pgvector table checks). `DATABASE_URL` (not `ASYNC_DATABASE_URL`) because
    psycopg.connect takes a `postgresql://` DSN, not the `+psycopg` SQLAlchemy
    dialect URL."""
    return psycopg.connect(settings.DATABASE_URL)
