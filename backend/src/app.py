import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from connectors.postgres import dispose_engine
from core.config import get_settings
from core.logging import configure_logging

app_logger = logging.getLogger("project_x.app")
request_logger = logging.getLogger("project_x.request")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    app_logger.info(
        "application.started",
        extra={
            "service": settings.project_name,
            "environment": settings.environment,
        },
    )
    yield
    await dispose_engine()
    app_logger.info(
        "application.stopped",
        extra={
            "service": settings.project_name,
            "environment": settings.environment,
        },
    )


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        lifespan=lifespan,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid4().hex)
        started_at = perf_counter()
        response = None

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            request_logger.exception(
                "request.failed",
                extra={
                    "request_id": request_id,
                    "service": settings.project_name,
                    "environment": settings.environment,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise
        finally:
            if response is not None:
                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                request_logger.info(
                    "request.completed",
                    extra={
                        "request_id": request_id,
                        "service": settings.project_name,
                        "environment": settings.environment,
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query),
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "client_ip": request.client.host if request.client else None,
                    },
                )

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_application()
