from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.order.repository import OrderRepository
from app.features.order.schemas import OrderResponse
from app.features.order.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderService:
    return OrderService(OrderRepository(session))


ServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    service: ServiceDep,
    integration_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[OrderResponse]:
    orders = await service.list(integration_id=integration_id, limit=limit, offset=offset)
    return [OrderResponse.model_validate(order) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, service: ServiceDep) -> OrderResponse:
    order = await service.get(order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return OrderResponse.model_validate(order)
