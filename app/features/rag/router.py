import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.rag.chat_repository import ChatRepository
from app.features.rag.chat_service import ChatService
from app.features.rag.schemas import AskRequest, AskResponse
from app.features.rag.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreateRequest,
    ChatSessionResponse,
)
from app.features.rag.service import RagService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/rag", tags=["rag"])
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_rag_service() -> RagService:
    return RagService()


def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatService:
    return ChatService(ChatRepository(session))


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


async def _get_owned_chat_session(
    service: ChatService,
    session_id: UUID,
    current_user: CurrentUser,
):
    chat_session = await service.get_session(
        session_id=session_id,
        company_id=current_user.company_id,
        user_id=current_user.id,
    )
    if chat_session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    return chat_session


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, current_user: CurrentUserDep) -> AskResponse:
    """Pergunta em linguagem natural ao Graph RAG. Roteia automaticamente
    entre busca vetorial local (LOCAL) e Cypher gerado dinamicamente pelo
    LLM para perguntas agregadas (GLOBAL) — ver `query_router.py`.

    Síncrono (não `BackgroundTasks`): diferente de `/graph-algorithms/run` e
    `/embeddings/run`, esta é uma consulta pontual pensada para responder
    dentro do próprio request."""
    service = get_rag_service()
    result = await service.ask(
        request.question, request.top_k, str(current_user.external_company_id)
    )
    return AskResponse.model_validate(result)


@router.post("/ask/stream")
async def ask_stream(request: AskRequest, current_user: CurrentUserDep) -> StreamingResponse:
    """Mesma pergunta de `/ask`, mas respondendo via Server-Sent Events
    conforme os tokens chegam da OpenAI, em vez de esperar a resposta
    inteira. Endpoint separado (não um parâmetro `stream=true` em `/ask`)
    porque o formato de resposta é fundamentalmente outro — SSE, não JSON —
    então merece um contrato próprio em vez de um `response_model` que
    mentiria sobre o corpo real.

    Eventos emitidos, um `data: {...}\\n\\n` por linha, cada um com um
    `type`:
    - `route`: `{"route": "LOCAL"|"GLOBAL"}` — primeiro evento, sempre.
    - `meta`: `{"sources": [...]}` (LOCAL) ou `{"generated_query": "..."}`
      (GLOBAL) — antes do primeiro `token`.
    - `token`: `{"text": "..."}` — um pedaço da resposta, repetido.
    - `error`: `{"message": "..."}` — se algo falhar no meio do caminho.
    - `done`: sinaliza fim do stream, sempre o último evento.

    POST (não GET/`EventSource`) porque o corpo tem `question`/`top_k` — a
    `EventSource` nativa do browser só faz GET, então o consumidor precisa
    ler via `fetch` + `ReadableStream`, não via `EventSource`."""
    service = get_rag_service()

    async def event_stream() -> AsyncIterator[str]:
        async for event in service.ask_stream(
            request.question, request.top_k, str(current_user.external_company_id)
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # desliga qualquer buffering de proxy (ex: nginx) no meio do
            # caminho — sem isso o stream chega inteiro de uma vez só.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    request: ChatSessionCreateRequest,
    service: ChatServiceDep,
    current_user: CurrentUserDep,
) -> ChatSessionResponse:
    chat_session = await service.create_session(
        company_id=current_user.company_id,
        user_id=current_user.id,
        title=request.title,
    )
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    service: ChatServiceDep,
    current_user: CurrentUserDep,
    limit: int = 30,
) -> list[ChatSessionResponse]:
    sessions = await service.list_sessions(current_user.company_id, current_user.id, limit)
    return [ChatSessionResponse.model_validate(chat_session) for chat_session in sessions]


@router.get("/chat/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: UUID,
    service: ChatServiceDep,
    current_user: CurrentUserDep,
) -> ChatHistoryResponse:
    chat_session = await _get_owned_chat_session(service, session_id, current_user)
    messages = await service.list_messages(chat_session.id)
    return ChatHistoryResponse(
        session=ChatSessionResponse.model_validate(chat_session),
        messages=[ChatMessageResponse.model_validate(message) for message in messages],
    )


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatResponse)
async def chat_message(
    session_id: UUID,
    request: ChatRequest,
    service: ChatServiceDep,
    current_user: CurrentUserDep,
) -> ChatResponse:
    chat_session = await _get_owned_chat_session(service, session_id, current_user)
    message, standalone_question = await service.ask(
        session=chat_session,
        message=request.message,
        top_k=request.top_k,
        company_id=str(current_user.external_company_id),
    )
    return ChatResponse(
        message=ChatMessageResponse.model_validate(message),
        standalone_question=standalone_question,
    )


@router.post("/chat/sessions/{session_id}/stream")
async def chat_message_stream(
    session_id: UUID,
    request: ChatRequest,
    service: ChatServiceDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    chat_session = await _get_owned_chat_session(service, session_id, current_user)

    async def event_stream() -> AsyncIterator[str]:
        async for event in service.ask_stream(
            session=chat_session,
            message=request.message,
            top_k=request.top_k,
            company_id=str(current_user.external_company_id),
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
