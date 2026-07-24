"""Business logic layer. `query_router.ask` is synchronous (OpenAI HTTP
calls + Neo4j driver calls, same as `app/core/infrastructure/database/neo4j.py`),
so it goes through `asyncio.to_thread` to avoid blocking the event loop.

No concurrency lock here (unlike `graph_algorithms`/`embeddings`): each call
is an independent, read-only request — there's no shared mutable state for
concurrent asks to race on.
"""

from __future__ import annotations

import asyncio

from app.features.rag.query_router import ask as ask_rag


class RagService:
    async def ask(self, question: str, top_k: int = 5) -> dict:
        return await asyncio.to_thread(ask_rag, question, top_k)
