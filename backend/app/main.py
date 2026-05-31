from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    audit_logs,
    auth,
    containers,
    naming,
    projects,
    uploads,
    workflows,
)
from app.core.config import settings
from app.db.base import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION)
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

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(containers.router, prefix=API_PREFIX)
app.include_router(audit_logs.router, prefix=API_PREFIX)
app.include_router(naming.router, prefix=API_PREFIX)
app.include_router(uploads.router, prefix=API_PREFIX)
app.include_router(workflows.router, prefix=API_PREFIX)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}
