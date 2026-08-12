"""Regression tests for the 2026-08 evaluation hardening pass."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.user import User


async def _register_and_login(
    client: AsyncClient, email: str, username: str
) -> tuple[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Hardening User",
            "password": "pass1234",
        },
    )
    user_id = reg.json()["id"]
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()["access_token"], user_id


async def _make_platform_admin(user_id: str) -> None:
    from sqlalchemy import update

    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_platform_admin=True)
        )
        await session.commit()


async def _create_org(name: str) -> str:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(Organization(id=org_id, name=name, slug=f"h-{org_id[:8]}"))
        await session.commit()
    return org_id


# ─── Admin user management ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_users_requires_platform_admin(client: AsyncClient):
    token, _ = await _register_and_login(client, "h_admin1@ex.com", "hadmin1")
    res = await client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_and_search(client: AsyncClient):
    token, user_id = await _register_and_login(client, "h_admin2@ex.com", "hadmin2")
    await _make_platform_admin(user_id)

    await _register_and_login(client, "h_search@ex.com", "hsearch")
    res = await client.get(
        "/api/v1/admin/users?q=hsearch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "h_search@ex.com"


@pytest.mark.asyncio
async def test_admin_update_user_membership_and_activation(client: AsyncClient):
    admin_token, admin_id = await _register_and_login(
        client, "h_admin3@ex.com", "hadmin3"
    )
    await _make_platform_admin(admin_id)
    _, target_id = await _register_and_login(client, "h_target@ex.com", "htarget")
    org_id = await _create_org("Hardening Org")

    res = await client.patch(
        f"/api/v1/admin/users/{target_id}",
        json={
            "is_active": False,
            "organization_id": org_id,
            "is_org_admin": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_active"] is False
    assert data["organizations"][0]["organization_id"] == org_id
    assert data["organizations"][0]["is_org_admin"] is True

    # Login must now be rejected for the deactivated user.
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "h_target@ex.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 403

    # Reactivate and remove membership.
    res2 = await client.patch(
        f"/api/v1/admin/users/{target_id}",
        json={"is_active": True, "remove_organization_id": org_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["is_active"] is True
    assert res2.json()["organizations"] == []


@pytest.mark.asyncio
async def test_admin_cannot_self_demote(client: AsyncClient):
    admin_token, admin_id = await _register_and_login(
        client, "h_admin4@ex.com", "hadmin4"
    )
    await _make_platform_admin(admin_id)
    res = await client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"is_platform_admin": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400


# ─── Audit CSV export ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_export_csv_requires_admin(client: AsyncClient):
    token, _ = await _register_and_login(client, "h_csv1@ex.com", "hcsv1")
    res = await client.get(
        "/api/v1/audit-logs/export.csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_audit_export_csv_returns_rows(client: AsyncClient):
    token, user_id = await _register_and_login(client, "h_csv2@ex.com", "hcsv2")
    await _make_platform_admin(user_id)

    res = await client.get(
        "/api/v1/audit-logs/export.csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    body = res.text
    assert body.startswith("\ufeff")
    assert "occurred_at" in body
    assert "user.login" in body


# ─── Metrics endpoint ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_endpoint_contains_request_counters(client: AsyncClient):
    await client.get("/health")
    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "bim_http_requests_total" in res.text
    assert "bim_app_info" in res.text


# ─── Self-registration control ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_disabled_returns_403(client: AsyncClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_SELF_REGISTRATION", False)
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@example.com",
            "username": "blockeduser",
            "full_name": "Blocked",
            "password": "pass1234",
        },
    )
    assert res.status_code == 403
    assert "Self-registration is disabled" in res.json()["detail"]


@pytest.mark.asyncio
async def test_register_enabled_by_default(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "openreg@example.com",
            "username": "openreguser",
            "full_name": "Open Reg",
            "password": "pass1234",
        },
    )
    assert res.status_code == 201
