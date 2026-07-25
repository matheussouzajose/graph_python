# syntax=docker/dockerfile:1

# Fixe uma versão em produção (ex.: --build-arg UV_VERSION=0.9.2) para builds
# reproduzíveis; :latest é conveniente mas muda sem aviso.
ARG UV_VERSION=latest
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# =============================================================================
# Stage 1: Builder — install dependencies with uv into a virtualenv
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer — only invalidated when deps change).
# --frozen: usa o uv.lock exatamente como está; falha se estiver dessincronizado.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime — minimal image, non-root user
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# curl/ca-certificates -> HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --no-create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appgroup /app

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/app ./app

# Config + scripts do Alembic — necessários para rodar `alembic upgrade head`
# dentro do container (env.py pega a URL do banco de app.core.config.settings).
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup migrations ./migrations

USER appuser

EXPOSE 8000

# Metadados de rastreio — preenchidos no build (ver scripts/release.sh).
ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
