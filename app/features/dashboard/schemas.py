from datetime import datetime

from pydantic import BaseModel


class OrderStatusCount(BaseModel):
    status: str
    count: int


class OverviewResponse(BaseModel):
    total_revenue: float
    total_orders: int
    average_ticket: float
    unique_customers: int
    products_sold: int
    orders_by_status: list[OrderStatusCount]
    last_order_sync_at: datetime | None
    last_algorithms_run_at: datetime | None


class TopSellingProduct(BaseModel):
    product_id: str
    product_name: str | None
    product_code: str | None
    quantity_sold: int


class TopRevenueProduct(BaseModel):
    product_id: str
    product_name: str | None
    product_code: str | None
    revenue: float


class TopPageRankProduct(BaseModel):
    product_id: str
    product_name: str | None
    product_code: str | None
    pagerank: float


class BoughtTogetherPair(BaseModel):
    product_id: str
    product_name: str | None
    product_code: str | None
    related_product_id: str
    related_product_name: str | None
    related_product_code: str | None
    support_count: int
    confidence: float
    lift: float


class RfmSegmentSummary(BaseModel):
    segment: str
    customer_count: int
    avg_recency_days: float | None
    avg_frequency: float | None
    avg_monetary: float | None


class CustomerSummary(BaseModel):
    customer_id: str
    name: str | None
    email: str | None
    document: str | None
    rfm_segment: str | None
    rfm_score: int | None
    rfm_recency_days: int | None
    rfm_frequency: int | None
    rfm_monetary: float | None
    last_order_at: datetime | None


class CustomerPurchasedProduct(BaseModel):
    product_id: str
    name: str | None
    code: str | None


class CustomerDetail(CustomerSummary):
    products_purchased: list[CustomerPurchasedProduct]


class IntegrationSyncStatus(BaseModel):
    integration_id: str
    integration_name: str
    provider: str
    status: str
    last_synced_at: datetime | None


class AlgorithmRunStatus(BaseModel):
    name: str
    computed_at: datetime | None


class SyncStatusResponse(BaseModel):
    integrations: list[IntegrationSyncStatus]
    algorithm_runs: list[AlgorithmRunStatus]
