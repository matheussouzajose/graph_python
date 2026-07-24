from fastapi import APIRouter, BackgroundTasks, status

from app.features.embeddings.schemas import EmbeddingsRunResponse
from app.features.embeddings.service import EmbeddingsService, is_run_running

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


def get_embeddings_service() -> EmbeddingsService:
    return EmbeddingsService()


@router.post(
    "/run",
    response_model=EmbeddingsRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_run(background_tasks: BackgroundTasks) -> EmbeddingsRunResponse:
    """Embeda (via OpenAI) todo Order/Product ainda sem `text_embedding` e
    cria/atualiza os vector indexes nativos do Neo4j. Roda como
    `BackgroundTasks` (em processo) — mesmo padrão de
    `POST /graph-algorithms/run` e `POST /orders/graph-sync`: chamada
    potencialmente longa e cara (uma requisição HTTP à OpenAI por lote), não
    deve bloquear a resposta.

    Se já existe um run em andamento, não enfileira outro."""
    if is_run_running():
        return EmbeddingsRunResponse(status="already_running")
    service = get_embeddings_service()
    background_tasks.add_task(service.run_pipeline)
    return EmbeddingsRunResponse(status="accepted")
