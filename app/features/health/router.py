from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.features.health.schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Liveness probe — returns basic service status."""
    return HealthResponse(
        status="ok",
        version=settings.API_V1_PREFIX,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(UTC),
    )
