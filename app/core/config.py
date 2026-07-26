"""Application settings — a single Pydantic ``BaseSettings`` model, read once
and cached.

Import ``settings`` for direct module-level access, or ``get_settings`` as a
FastAPI dependency (e.g. ``Annotated[Settings, Depends(get_settings)]``).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TITLE: str = "Base de conhecimentos de grafos"
    DESCRIPTION: str = "Base de conhecimentos de grafos API."
    IS_DEBUG: bool = False
    ENVIRONMENT: str = Field("local", description="Deployment environment name.")
    TIMEZONE: str = "America/Sao_Paulo"
    APP_VERSION: str = "v1"
    API_V1_PREFIX: str = "/api/v1"

    # Cache
    REDIS_HOST: str = Field("redis", description="Redis host.")
    REDIS_PORT: int = Field(6379, description="Redis port.")
    REDIS_PASSWORD: str | None = Field(
        None, description="Redis password. Use null for no auth."
    )

    # Auth / JWT
    JWT_SECRET_KEY: str = Field(
        "change-me-in-prod", description="Secret used to sign JWT access tokens."
    )
    JWT_ALGORITHM: str = Field("HS256", description="JWT signing algorithm.")
    JWT_EXPIRE_MINUTES: int = Field(
        60, description="Access token lifetime in minutes."
    )

    # OpenAI (chat + embeddings, RAG pipeline)
    OPENAI_API_KEY: str = Field("", description="API key for OpenAI.")
    OPENAI_CHAT_MODEL: str = Field(
        "gpt-4.1-mini", description="OpenAI chat model for the RAG pipeline."
    )
    OPENAI_EMBEDDING_MODEL: str = Field(
        "text-embedding-3-small", description="OpenAI embedding model for indexing/retrieval."
    )
    OPENAI_EMBEDDING_DIMENSIONS: int = Field(
        1536,
        description=(
            "Dimensionality requested from OPENAI_EMBEDDING_MODEL and configured on the Neo4j "
            "vector index — passed explicitly to the embeddings API call so the two can never "
            "drift out of sync."
        ),
    )

    # OpenRouter (alternate image-to-video provider — see
    # app/features/agents/video_providers/openrouter.py). Fronts several
    # vendors (Veo, Kling, Wan, ...) behind one API, unlike OPENAI_API_KEY
    # above which only talks to Sora.
    OPENROUTER_API_KEY: str = Field("", description="API key for OpenRouter (video generation).")

    # Database
    DBNAME: str = Field("", description="PostgreSQL database name.")
    DB_USER: str = Field("", description="PostgreSQL user.")
    DB_PASSWORD: str = Field("", description="PostgreSQL password.")
    DB_HOST: str = Field("", description="PostgreSQL host.")
    DB_PORT: int = Field("", description="PostgreSQL port.")

    # Neo4j
    NEO4J_URI: str = Field("", description="")
    NEO4J_USER: str = Field("", description="")
    NEO4J_PASSWORD: str = Field("", description="")

    # Orders API (external, study)
    ORDERS_API_BASE_URL: str = Field("", description="Base URL da API externa de pedidos.")
    ORDERS_API_TOKEN: str = Field("", description="API key da API externa de pedidos.")

    @property
    def set_app_attributes(self) -> dict[str, str | bool | None]:
        return {
            "title": self.TITLE,
            "debug": self.IS_DEBUG,
            "description": self.DESCRIPTION,
            "version": self.APP_VERSION,
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DBNAME}?sslmode=disable"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DBNAME}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
