from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text as sa_text

from app.api.v1 import (
    admin,
    audit_logs,
    auth,
    containers,
    naming,
    naming_rules,
    notifications,
    oidc,
    organizations,
    projects,
    rbac,
    reports,
    requirements,
    share_requests,
    uploads,
    workflows,
)
from app.core.config import settings
from app.core.metrics import MetricsMiddleware, render_metrics
from app.db.base import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION)
    # Ensure MinIO bucket exists once at startup (not per-request)
    try:
        from app.services.storage import ensure_bucket_exists

        ensure_bucket_exists()
        logger.info("storage_bucket_ready", bucket=settings.MINIO_BUCKET)
    except Exception as exc:
        logger.warning("storage_bucket_unavailable", error=str(exc))
    yield
    await engine.dispose()
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ISO 19650-compliant BIM Information Platform API",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(containers.router, prefix=API_PREFIX)
app.include_router(naming_rules.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(audit_logs.router, prefix=API_PREFIX)
app.include_router(naming.router, prefix=API_PREFIX)
app.include_router(rbac.router, prefix=API_PREFIX)
app.include_router(uploads.router, prefix=API_PREFIX)
app.include_router(workflows.router, prefix=API_PREFIX)
app.include_router(organizations.router, prefix=API_PREFIX)
app.include_router(requirements.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(oidc.router, prefix=API_PREFIX)
app.include_router(share_requests.router, prefix=API_PREFIX)
app.include_router(share_requests.public_router, prefix=API_PREFIX)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=render_metrics(),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    database = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
    except Exception:
        database = "error"

    redis = "unavailable"
    try:
        from redis.asyncio import from_url

        redis_client = from_url(settings.REDIS_URL, socket_connect_timeout=1)
        try:
            if await redis_client.ping():
                redis = "ok"
        finally:
            await redis_client.aclose()  # type: ignore[attr-defined]
    except Exception:
        redis = "unavailable"

    healthy = database == "ok"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "version": settings.APP_VERSION,
            "database": database,
            "redis": redis,
        },
    )
