"""Business logic layer. `query_router.ask` is synchronous (OpenAI HTTP
calls + Neo4j driver calls, same as `app/core/infrastructure/database/neo4j.py`),
so it goes through `asyncio.to_thread` to avoid blocking the event loop.

No concurrency lock here (unlike `graph_algorithms`/`embeddings`): each call
is an independent, read-only request — there's no shared mutable state for
concurrent asks to race on.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator

from app.features.rag.query_router import ask as ask_rag
from app.features.rag.query_router import ask_stream as ask_rag_stream

# Sentinel distinto de qualquer evento real, pra sinalizar "generator
# terminou" sem confundir com um evento {"type": ...} de verdade.
_STREAM_DONE = object()


class RagService:
    async def ask(self, question: str, top_k: int = 5, company_id: str | None = None) -> dict:
        return await asyncio.to_thread(ask_rag, question, top_k, company_id)

    async def ask_stream(
        self, question: str, top_k: int = 5, company_id: str | None = None
    ) -> AsyncIterator[dict]:
        """`ask_rag_stream` é um generator síncrono (cada `yield` pode ter
        bloqueado em I/O de rede — Neo4j ou OpenAI) — `asyncio.to_thread` só
        serve pra uma chamada que retorna um valor só, não pra iterar um
        generator item a item. Por isso a ponte manual aqui: o generator
        síncrono roda inteiro numa thread própria, e cada item que ele
        produz é empurrado pra uma `asyncio.Queue` via `call_soon_threadsafe`
        (a única forma segura de tocar o loop de fora da thread do loop);
        este método só drena a fila e repassa pro chamador assíncrono."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run() -> None:
            try:
                for event in ask_rag_stream(question, top_k, company_id):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _STREAM_DONE)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            event = await queue.get()
            if event is _STREAM_DONE:
                break
            yield event
