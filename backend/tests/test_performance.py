"""Performance baseline tests — assert key endpoints respond within budget.

These are coarse smoke-level latency checks (single-process, SQLite) to catch
gross regressions, NOT production load benchmarks. Budgets are generous to avoid
CI flakiness; tighten once a production-like perf environment exists.
"""

import time

import pytest
from httpx import AsyncClient

# Latency budgets (seconds) — generous to avoid CI flakiness
HEALTH_BUDGET = 0.5
AUTH_BUDGET = 3.0  # bcrypt hashing is intentionally slow
NAMING_BUDGET = 1.0


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": email.split("@")[0],
            "full_name": "Perf User",
            "password": "pass1234",
        },
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_health_latency(client: AsyncClient):
    start = time.perf_counter()
    res = await client.get("/health")
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < HEALTH_BUDGET, (
        f"/health took {elapsed:.3f}s (budget {HEALTH_BUDGET}s)"
    )


@pytest.mark.asyncio
async def test_login_latency(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "perf@example.com",
            "username": "perfuser",
            "full_name": "Perf",
            "password": "pass1234",
        },
    )
    start = time.perf_counter()
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "perf@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < AUTH_BUDGET, f"login took {elapsed:.3f}s (budget {AUTH_BUDGET}s)"


@pytest.mark.asyncio
async def test_naming_validate_latency(client: AsyncClient):
    token = await _token(client, "perfnaming@example.com")
    start = time.perf_counter()
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < NAMING_BUDGET, (
        f"naming validate took {elapsed:.3f}s (budget {NAMING_BUDGET}s)"
    )


@pytest.mark.asyncio
async def test_project_list_latency(client: AsyncClient):
    token = await _token(client, "perfproj@example.com")
    start = time.perf_counter()
    res = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < NAMING_BUDGET, (
        f"project list took {elapsed:.3f}s (budget {NAMING_BUDGET}s)"
    )
