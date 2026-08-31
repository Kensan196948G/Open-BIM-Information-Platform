from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_readiness_accepts_configured_dependencies(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setattr(settings, "AV_ENABLED", False)
    monkeypatch.setattr("app.main._storage_readiness", AsyncMock(return_value="ok"))

    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "version": settings.APP_VERSION,
        "database": "ok",
        "redis": "disabled",
        "storage": "ok",
        "antivirus": "disabled",
    }


@pytest.mark.asyncio
async def test_readiness_rejects_storage_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setattr(settings, "AV_ENABLED", False)
    monkeypatch.setattr(
        "app.main._storage_readiness", AsyncMock(return_value="unavailable")
    )

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["storage"] == "unavailable"


@pytest.mark.asyncio
async def test_readiness_rejects_required_redis_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(settings, "AV_ENABLED", False)
    monkeypatch.setattr(
        "app.main._redis_readiness", AsyncMock(return_value="unavailable")
    )
    monkeypatch.setattr("app.main._storage_readiness", AsyncMock(return_value="ok"))

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["redis"] == "unavailable"


@pytest.mark.asyncio
async def test_readiness_rejects_enabled_antivirus_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setattr(settings, "AV_ENABLED", True)
    monkeypatch.setattr("app.main._storage_readiness", AsyncMock(return_value="ok"))
    monkeypatch.setattr(
        "app.main._antivirus_readiness", AsyncMock(return_value="unavailable")
    )

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["antivirus"] == "unavailable"
