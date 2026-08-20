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


# ─── Refresh / logout / rate limiting ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient):
    """Refresh returns a new pair and revokes the presented refresh token."""
    await _register(client, "refresh@example.com", "refreshuser")
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "refresh@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    old_refresh = login_res.json()["refresh_token"]

    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"] != old_refresh

    # Rotated token must no longer be accepted.
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_access_token(client: AsyncClient):
    """After logout, the access token is rejected by /me."""
    await _register(client, "logout@example.com", "logoutuser")
    token = await _login(client, "logout@example.com")

    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 204

    me_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limited_after_limit(client: AsyncClient):
    """Rapid repeated logins from the same IP return 429."""
    await _register(client, "ratelimit@example.com", "ratelimituser")
    responses = []
    for _ in range(6):
        res = await client.post(
            "/api/v1/auth/login",
            data={"username": "ratelimit@example.com", "password": "pass1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        responses.append(res.status_code)
    assert responses.count(429) >= 1
    assert responses[0] == 200


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(client: AsyncClient):
    """Garbage refresh token returns 401."""
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_change_password_success_and_relogin(client: AsyncClient):
    """Change password then log in with the new password (old one fails)."""
    await _register(client, "changepw@example.com", "changepwuser")
    token = await _login(client, "changepw@example.com")

    res = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "pass1234",
            "new_password": "NewPass5678",
            "new_password_confirm": "NewPass5678",
        },
    )
    assert res.status_code == 204

    # Old password must now fail
    old = await client.post(
        "/api/v1/auth/login",
        data={"username": "changepw@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert old.status_code == 401

    # New password must succeed
    new = await client.post(
        "/api/v1/auth/login",
        data={"username": "changepw@example.com", "password": "NewPass5678"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_400(client: AsyncClient):
    await _register(client, "wrongpw@example.com", "wrongpwuser")
    token = await _login(client, "wrongpw@example.com")

    res = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrong-current",
            "new_password": "NewPass5678",
            "new_password_confirm": "NewPass5678",
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_change_password_mismatch_returns_400(client: AsyncClient):
    await _register(client, "mismatch@example.com", "mismatchuser")
    token = await _login(client, "mismatch@example.com")

    res = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "pass1234",
            "new_password": "NewPass5678",
            "new_password_confirm": "Different5678",
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "pass1234",
            "new_password": "NewPass5678",
            "new_password_confirm": "NewPass5678",
        },
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# MVP 公開デモ用のログイン認証バイパス (POST /api/v1/auth/demo-login)
# ---------------------------------------------------------------------------


async def test_demo_login_disabled_by_default(client: AsyncClient):
    """既定では経路の存在自体を隠す 404。"""
    from app.core.config import settings

    assert settings.AUTH_BYPASS is False
    res = await client.post("/api/v1/auth/demo-login")
    assert res.status_code == 404


async def test_demo_login_issues_token_when_enabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """有効化した環境では資格情報なしでトークンが払い出され、/me が通る。"""
    from app.core.config import settings

    await _register(client, email="demo@example.com", username="demouser")
    monkeypatch.setattr(settings, "AUTH_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "mvp")

    res = await client.post("/api/v1/auth/demo-login")
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200


async def test_demo_login_never_bypasses_production(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """ENVIRONMENT=production では AUTH_BYPASS=True でも必ず 404（安全装置）。"""
    from app.core.config import settings

    await _register(client, email="prod@example.com", username="produser")
    monkeypatch.setattr(settings, "AUTH_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    res = await client.post("/api/v1/auth/demo-login")
    assert res.status_code == 404


async def test_demo_login_unknown_email_fails_closed(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """AUTH_BYPASS_EMAIL に該当者が居なければ払い出さない。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "mvp")
    monkeypatch.setattr(settings, "AUTH_BYPASS_EMAIL", "nobody@example.invalid")

    res = await client.post("/api/v1/auth/demo-login")
    assert res.status_code == 404
