from fastapi import APIRouter

from app.features.rag.schemas import AskRequest, AskResponse
from app.features.rag.service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


def get_rag_service() -> RagService:
    return RagService()


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Pergunta em linguagem natural ao Graph RAG. Roteia automaticamente
    entre busca vetorial local (LOCAL) e Cypher gerado dinamicamente pelo
    LLM para perguntas agregadas (GLOBAL) — ver `query_router.py`.

    Síncrono (não `BackgroundTasks`): diferente de `/graph-algorithms/run` e
    `/embeddings/run`, esta é uma consulta pontual pensada para responder
    dentro do próprio request."""
    service = get_rag_service()
    result = await service.ask(request.question, request.top_k)
    return AskResponse.model_validate(result)
