import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "test@example.com") -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": "testuser",
            "full_name": "Test User",
            "password": "pass1234",
        },
    )
    assert res.status_code == 201
    return res.json()


async def _login(client: AsyncClient, email: str = "test@example.com") -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    data = await _register(client)
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await _register(client)
    token = await _login(client)
    assert token


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await _register(client)
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    await _register(client)
    token = await _login(client)
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
