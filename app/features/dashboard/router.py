from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.dashboard.schemas import (
    BoughtTogetherPair,
    CustomerDetail,
    CustomerSummary,
    OverviewResponse,
    RfmSegmentSummary,
    SyncStatusResponse,
    TopPageRankProduct,
    TopRevenueProduct,
    TopSellingProduct,
)
from app.features.dashboard.service import DashboardService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardService:
    return DashboardService(session)


ServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(service: ServiceDep, current_user: CurrentUserDep) -> OverviewResponse:
    """KPIs executivos: faturamento, pedidos, ticket médio, clientes
    compradores, produtos vendidos, status dos pedidos, última sincronização
    de pedidos e última execução dos algoritmos de grafo."""
    return await service.get_overview(current_user.company_id, current_user.external_company_id)


@router.get("/products/top-selling", response_model=list[TopSellingProduct])
async def top_selling_products(
    service: ServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=100),
) -> list[TopSellingProduct]:
    return await service.top_selling_products(current_user.external_company_id, limit)


@router.get("/products/top-revenue", response_model=list[TopRevenueProduct])
async def top_revenue_products(
    service: ServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=100),
) -> list[TopRevenueProduct]:
    return await service.top_revenue_products(current_user.external_company_id, limit)


@router.get("/products/top-pagerank", response_model=list[TopPageRankProduct])
async def top_pagerank_products(
    service: ServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=100),
) -> list[TopPageRankProduct]:
    """Vazio até `POST /graph-algorithms/run` rodar pelo menos uma vez —
    `pagerank` só existe no nó `Product` depois do batch job."""
    return await service.top_pagerank_products(current_user.external_company_id, limit)


@router.get("/products/bought-together", response_model=list[BoughtTogetherPair])
async def bought_together(
    service: ServiceDep,
    current_user: CurrentUserDep,
    product_id: str | None = None,
    limit: int = Query(10, ge=1, le=100),
) -> list[BoughtTogetherPair]:
    """Pares `BOUGHT_WITH`. Sem `product_id`: top pares globais por lift.
    Com `product_id`: só os pares daquele produto. Vazio até
    `POST /graph-algorithms/run` (que inclui association rules) rodar."""
    return await service.bought_together(current_user.external_company_id, product_id, limit)


@router.get("/customers/rfm-summary", response_model=list[RfmSegmentSummary])
async def rfm_summary(service: ServiceDep, current_user: CurrentUserDep) -> list[RfmSegmentSummary]:
    """Vazio até `POST /graph-algorithms/run` (ou `/graph-algorithms/rfm/run`)
    rodar pelo menos uma vez."""
    return await service.rfm_summary(current_user.external_company_id)


@router.get("/customers", response_model=list[CustomerSummary])
async def list_customers(
    service: ServiceDep,
    current_user: CurrentUserDep,
    segment: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CustomerSummary]:
    """Só retorna clientes com RFM já calculado — segmento é opcional."""
    return await service.list_customers(current_user.external_company_id, segment, limit, offset)


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: str, service: ServiceDep, current_user: CurrentUserDep
) -> CustomerDetail:
    customer = await service.get_customer(current_user.external_company_id, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.get("/sync-status", response_model=SyncStatusResponse)
async def sync_status(service: ServiceDep, current_user: CurrentUserDep) -> SyncStatusResponse:
    """Status de sincronização por integração (ERP -> Postgres) e a última
    execução de cada algoritmo de grafo (`AlgorithmRun`, gravado por
    `graph_algorithms/gds.py`)."""
    return await service.sync_status(current_user.company_id, current_user.external_company_id)
