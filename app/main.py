from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from starlette.types import Lifespan

from .core.cache import CacheProtocol
from .core.config import Settings, settings
from .core.exceptions import register_exception_handlers
from .core.infrastructure.cache.cache_service import RedisCacheService
from .core.infrastructure.database.extensions import enable_vector_extension
from .core.infrastructure.database.neo4j import close_driver, setup_schema
from .core.logger import logger
from .core.middleware import LoggingMiddleware
from .features.company.router import router as company_router
from .features.dashboard.router import router as dashboard_router
from .features.embeddings.router import router as embeddings_router
from .features.graph_algorithms.router import router as graph_algorithms_router
from .features.health.router import router as health_router
from .features.integration.router import router as integration_router
from .features.order.router import router as order_router
from .features.rag.router import router as rag_router
from .features.user.router import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await enable_vector_extension()
    await setup_schema()
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        logger.info("Checkpointer setup complete", db=settings.DBNAME)
        yield
        close_driver()
        logger.info("Checkpointer connection closed")


class App:
    def __init__(
        self,
        settings: Settings,
        cache: CacheProtocol | None = None,
        lifespan: Lifespan[FastAPI] | None = None,
    ):
        self.settings = settings
        self.__app = FastAPI(**settings.set_app_attributes, lifespan=lifespan)
        self.__app.state.cache = cache
        self.__setup_middleware()
        self.__add_routes()

    def __setup_middleware(self):
        self.__app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.__app.add_middleware(LoggingMiddleware)

    def __add_routes(self):
        self.__app.include_router(router=health_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=company_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=integration_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=user_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=dashboard_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=order_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=graph_algorithms_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=embeddings_router, prefix=settings.API_V1_PREFIX)
        self.__app.include_router(router=rag_router, prefix=settings.API_V1_PREFIX)

    def __call__(self) -> FastAPI:
        return self.__app


def initialize_application() -> FastAPI:
    cache = RedisCacheService()
    app = App(settings=settings, cache=cache, lifespan=lifespan)()
    register_exception_handlers(app)
    return app


app = initialize_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
