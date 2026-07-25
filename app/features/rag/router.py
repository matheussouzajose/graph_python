import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.features.rag.schemas import AskRequest, AskResponse
from app.features.rag.service import RagService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/rag", tags=["rag"])
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_rag_service() -> RagService:
    return RagService()


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
