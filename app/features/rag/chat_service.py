"""Conversational Oráculo chat with persisted history and LangChain memory."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Sequence
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.features.rag.chat_orm import ChatMessageORM, ChatSessionORM
from app.features.rag.chat_repository import ChatRepository
from app.features.rag.query_router import ask as ask_rag
from app.features.rag.query_router import ask_stream as ask_rag_stream

_STREAM_DONE = object()

MEMORY_SYSTEM_PROMPT = """Você transforma perguntas de acompanhamento em perguntas completas.
Use o histórico apenas para recuperar referências como "esse produto",
"essa cidade", "o mesmo período" ou "eles". Não responda à pergunta final.
Se a nova pergunta já estiver completa, devolva ela quase igual.

Devolva somente a pergunta reescrita em português, sem comentários."""

FRIENDLY_SYSTEM_PROMPT = """Você melhora uma resposta analítica para soar como um consultor comercial.
Preserve todos os fatos, números, nomes, códigos, fontes e limitações da resposta original.
Não invente dados. Se a resposta original disser que não há dados suficientes, mantenha essa cautela.
Escreva em português claro, direto e amigável.
Prefira:
- conclusão primeiro;
- bullets curtos quando houver mais de uma ação;
- recomendações práticas quando a evidência permitir."""


class ChatService:
    def __init__(self, repository: ChatRepository) -> None:
        self._repository = repository
        self._llm = ChatOpenAI(
            model=settings.OPENAI_CHAT_MODEL,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )

    async def create_session(
        self, company_id: UUID, user_id: UUID, title: str | None = None
    ) -> ChatSessionORM:
        clean_title = (title or "Nova conversa").strip()[:255] or "Nova conversa"
        return await self._repository.create_session(company_id, user_id, clean_title)

    async def list_sessions(
        self, company_id: UUID, user_id: UUID, limit: int = 30
    ) -> Sequence[ChatSessionORM]:
        return await self._repository.list_sessions(company_id, user_id, limit)

    async def get_session(
        self, session_id: UUID, company_id: UUID, user_id: UUID
    ) -> ChatSessionORM | None:
        return await self._repository.get_session(session_id, company_id, user_id)

    async def list_messages(self, session_id: UUID) -> Sequence[ChatMessageORM]:
        return await self._repository.list_messages(session_id)

    async def ask(
        self,
        session: ChatSessionORM,
        message: str,
        top_k: int,
        company_id: str,
    ) -> tuple[ChatMessageORM, str]:
        question = message.strip()
        history = await self._repository.recent_messages(session.id)
        standalone_question = await self._standalone_question(question, history)
        await self._repository.add_message(session.id, "user", question)

        result = await asyncio.to_thread(ask_rag, standalone_question, top_k, company_id)
        friendly_answer = await self._friendly_answer(question, result.get("answer") or "")
        assistant = await self._repository.add_message(
            session.id,
            "assistant",
            friendly_answer,
            route=result.get("route"),
            generated_query=result.get("generated_query"),
            sources=result.get("sources"),
        )
        return assistant, standalone_question

    async def ask_stream(
        self,
        session: ChatSessionORM,
        message: str,
        top_k: int,
        company_id: str,
    ) -> AsyncIterator[dict]:
        question = message.strip()
        history = await self._repository.recent_messages(session.id)
        standalone_question = await self._standalone_question(question, history)
        await self._repository.add_message(session.id, "user", question)
        yield {"type": "question", "standalone_question": standalone_question}

        route: str | None = None
        generated_query: str | None = None
        sources: list | None = None
        answer_parts: list[str] = []

        async for event in self._rag_stream(standalone_question, top_k, company_id):
            event_type = event.get("type")
            if event_type == "route":
                route = event.get("route")
            elif event_type == "meta":
                generated_query = event.get("generated_query", generated_query)
                sources = event.get("sources", sources)
            elif event_type == "token":
                answer_parts.append(event.get("text", ""))
            elif event_type == "done":
                continue
            yield event

        raw_answer = "".join(answer_parts)
        friendly_answer = (
            await self._friendly_answer(question, raw_answer) if raw_answer.strip() else raw_answer
        )
        if friendly_answer and friendly_answer != raw_answer:
            yield {"type": "replace", "text": friendly_answer}

        await self._repository.add_message(
            session.id,
            "assistant",
            friendly_answer or raw_answer or "Não consegui gerar uma resposta.",
            route=route,
            generated_query=generated_query,
            sources=sources,
        )
        yield {"type": "done"}

    async def _standalone_question(
        self, question: str, history: Sequence[ChatMessageORM]
    ) -> str:
        if len(history) < 2:
            return question

        messages = trim_messages(
            self._to_langchain_messages(history),
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=1600,
            start_on="human",
            end_on=("human", "ai"),
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", MEMORY_SYSTEM_PROMPT),
                MessagesPlaceholder("history"),
                ("human", "Nova pergunta: {question}"),
            ]
        )
        chain = prompt | self._llm
        response = await asyncio.to_thread(
            chain.invoke,
            {"history": messages, "question": question},
        )
        rewritten = (response.content or "").strip()
        return rewritten or question

    async def _friendly_answer(self, question: str, answer: str) -> str:
        if not answer.strip():
            return answer
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", FRIENDLY_SYSTEM_PROMPT),
                (
                    "human",
                    "Pergunta original:\n{question}\n\nResposta técnica:\n{answer}\n\n"
                    "Reescreva a resposta para o usuário final.",
                ),
            ]
        )
        chain = prompt | self._llm
        response = await asyncio.to_thread(chain.invoke, {"question": question, "answer": answer})
        friendly = (response.content or "").strip()
        return friendly or answer

    async def _rag_stream(
        self, question: str, top_k: int, company_id: str
    ) -> AsyncIterator[dict]:
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

    def _to_langchain_messages(self, messages: Sequence[ChatMessageORM]) -> list[BaseMessage]:
        output: list[BaseMessage] = []
        for message in messages:
            if message.role == "user":
                output.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                output.append(AIMessage(content=message.content))
        return output
