import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.api.v1.router import api_router
from app.core.config import Settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    AuthRateLimitMiddleware,
    BodySizeLimitMiddleware,
    RequestIdMiddleware,
    SecurityResponseHeadersMiddleware,
)
from app.core.request_context import REQUEST_ID_HEADER
from app.db.session import Database

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory. Rodar com: uvicorn app.main:create_app --factory --reload"""
    settings = settings or Settings()
    configure_logging(settings.log_level)
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application starting",
            extra={
                "app_env": settings.app_env.value,
                "database": settings.safe_database_url,
            },
        )
        yield
        database.dispose()
        logger.info("application stopped")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.database = database

    # Ordem: o último adicionado é o mais externo.
    # CORS (externo) -> RequestId -> AuthRateLimit -> BodySizeLimit -> app
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(AuthRateLimitMiddleware, database=database, settings=settings)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        SecurityResponseHeadersMiddleware, production=settings.is_production
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", REQUEST_ID_HEADER, "Authorization"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app
