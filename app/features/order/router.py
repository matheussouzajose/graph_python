from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.order.graph_sync import is_graph_sync_running, run_graph_sync
from app.features.order.repository import OrderRepository
from app.features.order.schemas import GraphSyncTriggerResponse, OrderResponse
from app.features.order.service import OrderService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderService:
    return OrderService(OrderRepository(session))


ServiceDep = Annotated[OrderService, Depends(get_order_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    service: ServiceDep,
    current_user: CurrentUserDep,
    integration_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[OrderResponse]:
    orders = await service.list_for_company(
        company_id=current_user.company_id,
        integration_id=integration_id,
        limit=limit,
        offset=offset,
    )
    return [OrderResponse.model_validate(order) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> OrderResponse:
    order = await service.get_for_company(order_id, current_user.company_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return OrderResponse.model_validate(order)


@router.post(
    "/graph-sync",
    response_model=GraphSyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_graph_sync(
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    integration_id: UUID | None = None,
) -> GraphSyncTriggerResponse:
    """Projeta pedidos já persistidos em `orders` (Postgres) pro Neo4j via
    `run_graph_sync`. Roda como `BackgroundTasks` (em processo), não como o
    evento durável do `POST /integrations/{id}/sync` — não sobrevive a um
    restart da API no meio do run. Aceitável aqui porque a fonte é o próprio
    Postgres (nada se perde: rodar de novo simplesmente reprocessa os
    mesmos pedidos, as escritas no grafo são idempotentes via MERGE).

    Se já existe um run em andamento, não enfileira outro — evita gastar um
    passe inteiro pelo Postgres à toa só pra ficar bloqueado esperando o lock
    de `run_graph_sync`; o caller pode tentar de novo depois."""
    if is_graph_sync_running():
        return GraphSyncTriggerResponse(status="already_running", integration_id=integration_id)
    background_tasks.add_task(
        run_graph_sync, integration_id=integration_id, company_id=current_user.company_id
    )
    return GraphSyncTriggerResponse(status="accepted", integration_id=integration_id)
