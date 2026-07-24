"""Business logic layer. `pipeline.py` calls are synchronous (same Neo4j
driver as `app/core/infrastructure/database/neo4j.py`, plus a blocking
OpenAI HTTP call), so every call here goes through `asyncio.to_thread` to
avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio

from app.features.embeddings.pipeline import run_embedding_pipeline

# Serializa execuções do pipeline dentro deste processo. Sem isso, dois
# triggers próximos reprocessariam a mesma leva de nós ainda sem
# `text_embedding` antes que a primeira chamada termine de escrever —
# trabalho (e custo de API OpenAI) duplicado à toa, não corrupção de dado
# (a escrita em si é idempotente via `SET`).
_run_lock = asyncio.Lock()


def is_run_running() -> bool:
    return _run_lock.locked()


class EmbeddingsService:
    async def run_pipeline(self) -> dict:
        async with _run_lock:
            return await asyncio.to_thread(run_embedding_pipeline)
