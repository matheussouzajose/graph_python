# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is an early-stage scaffold ("Base de conhecimentos de grafos" / graph knowledge base API) built on
top of a media-processing project template. Only the `health` feature slice is implemented today.
Several things referenced by the scaffolding do **not exist yet** in this repo — don't assume they do:

- `app/core/infrastructure/database/registry.py` imports `app.features.auth.orm`,
  `app.features.processing.orm`, `app.features.videos.orm` — none of these feature packages exist yet.
  This module will break on import until those slices are added.
- There is no `migrations/` directory or `alembic.ini` yet, even though `alembic` is a dependency and
  the Dockerfile has commented-out `COPY` lines for them.
- There is no `tests/` directory yet, even though `pyproject.toml` sets `testpaths = ["tests"]` and dev
  dependencies include `pytest`/`pytest-asyncio`/`pytest-cov`. **Do not create tests or a `tests/`
  directory unless explicitly asked to.** The testing setup is scaffolded for later, not now.
- The messaging module (`app/core/infrastructure/messaging/`) is a Redis Streams + transactional-outbox
  implementation built for video pipeline events (`video.created`, `video.downloaded`, ...) — it's
  generic plumbing carried over from the template, not yet wired to any graph/RAG domain events.
- `pyproject.toml` excludes `app/engine` from ruff/mypy as "vendored code (viral_cutter_v3)", but that
  directory isn't present in this checkout.

When adding a new feature, follow the existing `app/features/health/` slice shape (`router.py` +
`schemas.py`, optionally `orm.py`/`service.py`) rather than inventing a new layout.

## Commands

Dependency management and running commands goes through `uv` (dependencies are declared in
`pyproject.toml`, locked in `uv.lock`).

```bash
uv sync                       # install/sync dependencies (uv.lock)
uv run uvicorn app.main:app --reload --port 8000   # run the API locally

uv run ruff check .           # lint (see [tool.ruff] for excludes/rules)
uv run ruff format .          # format
uv run mypy .                 # type check (strict mode; excludes app/engine)
uv run pytest                 # run tests (once tests/ exists)
uv run pytest path/to/test_file.py::test_name   # run a single test
```

Full stack (Postgres+pgvector, Redis, Neo4j, API) via Docker:

```bash
docker compose up --build
```

The API container mounts `./app` as a live volume and runs `uvicorn --reload`, so code changes apply
without a rebuild; only dependency changes require `--build`.

## Architecture

**Layout**: `app/core/` holds cross-cutting infrastructure; `app/features/` holds vertical feature
slices (one package per domain feature, each with its own `router.py`/`schemas.py`/etc.). `app/main.py`
wires everything together — settings, cache, middleware, exception handlers, and each feature's router
are assembled in `initialize_application()`.

**Settings** (`app/core/config.py`): a single Pydantic `Settings` (`BaseSettings`) model reads `.env`
once. Import the module-level `settings` singleton directly, or inject `Settings` via
`Depends(get_settings)` in routes (see `health/router.py`) so tests can override it.

**Database** (`app/core/infrastructure/database/`):
- `base.py` — the shared SQLAlchemy `DeclarativeBase`; every ORM model must inherit from it.
- `session.py` — one process-wide async `engine` + `AsyncSessionFactory`; `get_session()` is the
  FastAPI dependency that yields a per-request `AsyncSession` and owns the transaction (commit on
  success, rollback on exception). Repositories/services receive the session and never manage
  transactions themselves.
- `registry.py` — import-side-effect module that pulls in every feature's `orm.py` so
  `Base.metadata` is complete for both Alembic and any standalone process (e.g. a worker) that
  doesn't go through the FastAPI app. **Any new feature with an ORM model must be added here.**
- `extensions.py` — one-off DDL (`CREATE EXTENSION IF NOT EXISTS vector`) run at app startup via the
  `lifespan` in `main.py`, before pgvector-typed columns are used.

There's also a `langgraph` `AsyncPostgresSaver` checkpointer set up in `main.py`'s `lifespan` and
stashed on `app.state.checkpointer` — this is the persistence layer for LangGraph agent state, separate
from the SQLAlchemy engine above.

**Messaging** (`app/core/infrastructure/messaging/`) — a provider-agnostic pattern: business code only
depends on the `Event`/`EventProducer`/`EventHandler` Protocols in `base.py`, never on Redis directly.
- `redis_stream.py` — `RedisStreamProducer`/`RedisStreamConsumer` over Redis Streams (consumer groups,
  explicit XACK, at-least-once delivery; handler exceptions leave the message unacked for redelivery).
- `outbox/` — transactional outbox pattern: `OutboxEventProducer` writes to the `outbox_events` table
  in the same DB transaction as the domain change (via the request-scoped session); `OutboxRelay`
  separately polls pending rows (`FOR UPDATE SKIP LOCKED`) and republishes them to the real stream.
  Use this producer instead of `RedisStreamProducer` directly whenever an event must be emitted
  atomically with a DB write.
- `client.py` / `events.py` — shared Redis client + stream/event-name constants (avoid typo'd stream
  names between producer and consumer).

**Cache** (`app/core/cache.py`, `app/core/infrastructure/cache/cache_service.py`): `CacheProtocol` is
the interface; `RedisCacheService` is the only implementation, instantiated once in
`initialize_application()` and stashed on `app.state.cache`.

**Logging & observability**:
- `app/core/logger.py` configures `structlog` routed through stdlib logging: JSON output in
  non-debug environments (for log pipelines), human-readable `ConsoleRenderer` when `IS_DEBUG=True`.
- `app/core/observability/masking.py` is the single source of truth for redacting sensitive fields
  (`password`, `token`, `secret`, `api_key`, `government_id`, etc.) from logs — applied both as a
  structlog processor (`mask_log_event`) and directly by `LoggingMiddleware`. Add new sensitive key
  names to `SENSITIVE_KEYS` here, not ad hoc at call sites.
- `app/core/middleware.py`'s `LoggingMiddleware` logs masked request/response bodies and timing for
  every request.

**Errors** (`app/core/exceptions.py`): all error responses share one JSON envelope,
`{"error": {"code", "message", "details"}}`, registered via `register_exception_handlers(app)`.
Unhandled exceptions log the full traceback but only return the exception detail to the client when
`IS_DEBUG=True`; otherwise a generic "Internal server error" message.

## Config notes

- External integrations already wired via `Settings` but not yet consumed by any feature code:
  OpenAI (chat + embeddings for a planned RAG pipeline), Neo4j (`NEO4J_*`, for the graph store), and
  an external "Orders API" (`ORDERS_API_*`, marked as "study" in `config.py`).
- `DATABASE_URL` (sync `postgresql://`, used by plain `psycopg` connections) and `ASYNC_DATABASE_URL`
  (`postgresql+psycopg://`, used by the SQLAlchemy async engine) are both derived from the same
  `DB_*` settings — pick the right one depending on whether the caller is sync or async SQLAlchemy.
