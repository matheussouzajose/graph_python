from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.features.graph_algorithms.schemas import (
    AssociationRulesRunRequest,
    AssociationRulesRunResponse,
    CustomerRecommendationRequest,
    GraphAlgorithmsRunResponse,
    PersonalizedPageRankRequest,
    PersonalizedPageRankResult,
    ProductRecommendationRequest,
    RecommendationResult,
    RfmRunResponse,
)
from app.features.graph_algorithms.service import GraphAlgorithmsService, is_run_running
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/graph-algorithms", tags=["graph-algorithms"])
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_graph_algorithms_service() -> GraphAlgorithmsService:
    return GraphAlgorithmsService()


@router.post(
    "/run",
    response_model=GraphAlgorithmsRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_run(
    background_tasks: BackgroundTasks, current_user: CurrentUserDep
) -> GraphAlgorithmsRunResponse:
    """Dispara o job em lote (FastRP+KNN, PageRank, Leiden) sobre o grafo
    Order/Product/Customer. Roda como `BackgroundTasks` (em processo) — este
    job é pensado pra ser agendado (cron/Airflow), este endpoint só existe
    pra permitir disparo manual/ad-hoc, mesmo padrão de
    `POST /orders/graph-sync`.

    Se já existe um run em andamento, não enfileira outro."""
    if is_run_running():
        return GraphAlgorithmsRunResponse(status="already_running")
    service = get_graph_algorithms_service()
    background_tasks.add_task(service.run_all, current_user.external_company_id)
    return GraphAlgorithmsRunResponse(status="accepted")


@router.post(
    "/rfm/run",
    response_model=RfmRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_rfm_run(
    background_tasks: BackgroundTasks, current_user: CurrentUserDep
) -> RfmRunResponse:
    """Calcula RFM estruturado de clientes sem depender de embeddings."""
    service = get_graph_algorithms_service()
    background_tasks.add_task(service.run_rfm, current_user.external_company_id)
    return RfmRunResponse(status="accepted")


@router.post(
    "/association-rules/run",
    response_model=AssociationRulesRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_association_rules_run(
    request: AssociationRulesRunRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
) -> AssociationRulesRunResponse:
    """Calcula regras produto -> produto com support, confidence e lift."""
    service = get_graph_algorithms_service()
    background_tasks.add_task(
        service.run_association_rules,
        current_user.external_company_id,
        request.min_support_count,
        request.min_confidence,
    )
    return AssociationRulesRunResponse(status="accepted")


@router.post("/personalized-pagerank", response_model=list[PersonalizedPageRankResult])
async def personalized_pagerank(
    request: PersonalizedPageRankRequest,
    current_user: CurrentUserDep,
) -> list[PersonalizedPageRankResult]:
    """PageRank personalizado em tempo real — usado por API/retriever, não
    pelo job em lote. `product_ids` são `Product.id` de domínio (ex: produtos
    que o cliente já comprou); requer que `/graph-algorithms/run` já tenha
    projetado o grafo desta empresa ao menos uma vez."""
    service = get_graph_algorithms_service()
    results = await service.personalized_pagerank(
        request.product_ids, request.limit, current_user.external_company_id
    )
    return [PersonalizedPageRankResult.model_validate(result) for result in results]


@router.post("/recommendations/product", response_model=list[RecommendationResult])
async def recommendations_by_product(
    request: ProductRecommendationRequest,
    current_user: CurrentUserDep,
) -> list[RecommendationResult]:
    """Recomendacao por produto usando grafo estrutural.

    Usa `SIMILAR_TO` quando o job de similaridade ja rodou e `BOUGHT_WITH`
    quando as regras de associacao ja foram calculadas. Embeddings podem
    melhorar `SIMILAR_TO`, mas nao sao obrigatorios para este endpoint.
    """
    service = get_graph_algorithms_service()
    results = await service.recommend_by_product(
        request.product_id, request.limit, current_user.external_company_id
    )
    return [RecommendationResult.model_validate(result) for result in results]


@router.post("/recommendations/customer", response_model=list[RecommendationResult])
async def recommendations_by_customer(
    request: CustomerRecommendationRequest,
    current_user: CurrentUserDep,
) -> list[RecommendationResult]:
    """Recomendacao por cliente baseada no historico de compras e RFM."""
    service = get_graph_algorithms_service()
    results = await service.recommend_by_customer(
        request.customer_id, request.limit, current_user.external_company_id
    )
    return [RecommendationResult.model_validate(result) for result in results]
