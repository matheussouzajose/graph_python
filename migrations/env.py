"""Alembic environment — async-aware.

Key points:
- The DB URL comes from the app settings (single source of truth).
- `target_metadata` is `Base.metadata`; every ORM model module must be
  imported here so its table is registered for `--autogenerate`.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import every ORM model so Base.metadata knows about its table.
# Add new features here (one import line per feature's orm.py).
import app.core.infrastructure.messaging.outbox.orm  # noqa: F401,E402
import app.features.company.orm  # noqa: F401,E402
import app.features.integration.orm  # noqa: F401,E402
from app.core.config import settings
from app.core.infrastructure.database.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables owned by other tools (LangGraph checkpointer) live in the same
# database but are NOT managed by Alembic. Excluding them keeps
# autogenerate from proposing to drop them.
_EXTERNAL_TABLES = {
    "checkpoints",
    "checkpoint_migrations",
    "checkpoint_blobs",
    "checkpoint_writes",
}


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001, ANN201
    return not (type_ == "table" and name in _EXTERNAL_TABLES)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=settings.ASYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
