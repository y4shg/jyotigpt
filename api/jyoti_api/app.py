"""FastAPI application factory for the JyotiGPT API server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from jyoti_api import __version__
from jyoti_api.api.router import api_router
from jyoti_api.config import get_settings
from jyoti_api.errors import ApiError

logger = logging.getLogger("jyoti_api")

_http_logger = logging.getLogger("jyoti_api.http")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from jyoti_api.persistence.database import SessionLocal, init_db
    from jyoti_api.domain.accounts import bootstrap_admin

    init_db()
    with SessionLocal() as session:
        bootstrap_admin(session)
    logger.info("JyotiGPT API started")
    yield
    logger.info("JyotiGPT API stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        _http_logger.info("%s %s", request.method, request.url.path)
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code, **({} if exc.extra is None else {"extra": exc.extra})},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request payload.", "code": "validation_error", "errors": exc.errors()},
        )

    app.include_router(api_router)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "app": settings.app_name, "version": __version__}

    return app


app = create_app()
