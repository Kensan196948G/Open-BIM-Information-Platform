"""Tests for /audit-logs endpoints."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.audit_log import AuditLog
from app.models.user import User

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _register_and_login(
    client: AsyncClient, email: str, username: str
) -> tuple[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Test User",
            "password": "pass1234",
        },
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    return res.json()["access_token"], user_id


async def _make_admin(user_id: str) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_platform_admin=True)
        )
        await session.commit()


async def _seed_log(
    actor_id: str | None = None,
    event_type: str = "project.created",
    target_type: str = "project",
    target_id: str | None = None,
) -> str:
    from tests.conftest import TestSessionLocal

    log_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(
            AuditLog(
                id=log_id,
                occurred_at="2026-01-01T00:00:00Z",
                event_type=event_type,
                actor_id=actor_id,
                actor_ip="127.0.0.1",
                target_type=target_type,
                target_id=target_id or str(uuid.uuid4()),
                operation="create",
                result="success",
            )
        )
        await session.commit()
    return log_id


# ─── Authorization ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    res = await client.get("/api/v1/audit-logs")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_audit_logs_non_admin_returns_403(client: AsyncClient):
    """Regular user (non-admin) receives 403."""
    token, _ = await _register_and_login(client, "regular@example.com", "regularuser")
    res = await client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


# ─── Admin access ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_admin_empty(client: AsyncClient):
    """Platform admin can list logs — empty DB returns empty list."""
    token, user_id = await _register_and_login(client, "admin@example.com", "adminuser")
    await _make_admin(user_id)
    res = await client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_audit_logs_returns_seeded_entry(client: AsyncClient):
    """Admin sees seeded log entry with correct fields."""
    token, user_id = await _register_and_login(
        client, "admin2@example.com", "adminuser2"
    )
    await _make_admin(user_id)
    log_id = await _seed_log(actor_id=user_id)
    res = await client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == log_id
    assert item["event_type"] == "project.created"
    assert item["actor_id"] == user_id
    assert item["result"] == "success"


# ─── Filter: event_type ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_filter_event_type_match(client: AsyncClient):
    """Filter by event_type returns only matching entries."""
    token, user_id = await _register_and_login(
        client, "admin3@example.com", "adminuser3"
    )
    await _make_admin(user_id)
    await _seed_log(event_type="project.created")
    await _seed_log(event_type="user.login")
    res = await client.get(
        "/api/v1/audit-logs",
        params={"event_type": "project.created"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "project.created"


@pytest.mark.asyncio
async def test_audit_logs_filter_event_type_no_match(client: AsyncClient):
    """Filter by non-existent event_type returns empty."""
    token, user_id = await _register_and_login(
        client, "admin4@example.com", "adminuser4"
    )
    await _make_admin(user_id)
    await _seed_log(event_type="project.created")
    res = await client.get(
        "/api/v1/audit-logs",
        params={"event_type": "nonexistent.event"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ─── Filter: target_type ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_filter_target_type(client: AsyncClient):
    """Filter by target_type returns only matching entries."""
    token, user_id = await _register_and_login(
        client, "admin5@example.com", "adminuser5"
    )
    await _make_admin(user_id)
    await _seed_log(target_type="project")
    await _seed_log(target_type="container")
    res = await client.get(
        "/api/v1/audit-logs",
        params={"target_type": "container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["target_type"] == "container"


# ─── Filter: target_id ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_filter_target_id(client: AsyncClient):
    """Filter by target_id narrows results correctly."""
    token, user_id = await _register_and_login(
        client, "admin6@example.com", "adminuser6"
    )
    await _make_admin(user_id)
    specific_id = str(uuid.uuid4())
    await _seed_log(target_id=specific_id)
    await _seed_log()  # different target_id
    res = await client.get(
        "/api/v1/audit-logs",
        params={"target_id": specific_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["target_id"] == specific_id


# ─── Pagination ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_pagination(client: AsyncClient):
    """Page/size parameters control result window."""
    token, user_id = await _register_and_login(
        client, "admin7@example.com", "adminuser7"
    )
    await _make_admin(user_id)
    for _ in range(5):
        await _seed_log()
    res = await client.get(
        "/api/v1/audit-logs",
        params={"page": 1, "size": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["size"] == 3


@pytest.mark.asyncio
async def test_audit_logs_pagination_page2(client: AsyncClient):
    """Second page returns remaining items."""
    token, user_id = await _register_and_login(
        client, "admin8@example.com", "adminuser8"
    )
    await _make_admin(user_id)
    for _ in range(4):
        await _seed_log()
    res = await client.get(
        "/api/v1/audit-logs",
        params={"page": 2, "size": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 1


# ─── Null actor (system events) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_null_actor(client: AsyncClient):
    """Log entries with null actor_id are returned correctly."""
    token, user_id = await _register_and_login(
        client, "admin9@example.com", "adminuser9"
    )
    await _make_admin(user_id)
    await _seed_log(actor_id=None)
    res = await client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["actor_id"] is None
