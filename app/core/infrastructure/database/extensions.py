"""One-off DDL that must run before any model uses the `vector` type."""

from sqlalchemy import text

from app.core.infrastructure.database.session import engine


async def enable_vector_extension() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
