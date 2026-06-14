import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.user import User


async def _register(
    client: AsyncClient,
    email: str = "test@example.com",
    username: str = "testuser",
) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
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


async def _disable_user(user_id: str) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
        await session.commit()


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


# ─── Register edge cases ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    """Second registration with same email returns 409 Conflict."""
    await _register(client, "dup@example.com", "dupuser1")
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "username": "dupuser2",
            "full_name": "Dup",
            "password": "pass1234",
        },
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_returns_no_password_field(client: AsyncClient):
    """UserResponse never exposes hashed_password."""
    data = await _register(client, "safe@example.com", "safeuser")
    assert "hashed_password" not in data
    assert "password" not in data


# ─── Login edge cases ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient):
    """Login with non-existent email returns 401."""
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled_account_returns_403(client: AsyncClient):
    """Disabled account cannot log in — returns 403."""
    data = await _register(client, "disabled@example.com", "disableduser")
    await _disable_user(data["id"])
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "disabled@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_login_returns_token_structure(client: AsyncClient):
    """Token response contains access_token, refresh_token and token_type."""
    await _register(client, "tok@example.com", "tokuser")
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "tok@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


# ─── /me edge cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient):
    """Unauthenticated /me request returns 401."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_returns_full_profile(client: AsyncClient):
    """GET /me returns id, email, username, full_name."""
    await _register(client, "me@example.com", "meuser")
    token = await _login(client, "me@example.com")
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me@example.com"
    assert data["username"] == "meuser"
    assert "id" in data
    assert "full_name" in data
