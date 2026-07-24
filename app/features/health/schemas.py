from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str
    version: str
    environment: str
    timestamp: datetime
