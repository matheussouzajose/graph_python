from pydantic import BaseModel


class GraphAlgorithmsRunResponse(BaseModel):
    status: str


class RfmRunResponse(BaseModel):
    status: str


class AssociationRulesRunRequest(BaseModel):
    min_support_count: int = 2
    min_confidence: float = 0.05


class AssociationRulesRunResponse(BaseModel):
    status: str


class PersonalizedPageRankRequest(BaseModel):
    product_ids: list[str]
    limit: int = 10


class PersonalizedPageRankResult(BaseModel):
    product_id: str
    product_name: str | None
    score: float


class ProductRecommendationRequest(BaseModel):
    product_id: str
    limit: int = 10


class CustomerRecommendationRequest(BaseModel):
    customer_id: str
    limit: int = 10


class RecommendationResult(BaseModel):
    product_id: str
    product_name: str | None
    product_code: str | None
    score: float
    reasons: list[str]
    similarity_score: float
    support_count: int
    confidence: float
    lift: float
    pagerank: float | None = None
    customer_segment: str | None = None
    customer_rfm_score: int | None = None
