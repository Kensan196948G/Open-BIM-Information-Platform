"""Tests for project naming rules API (Issue #3)."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization


async def _setup_org_project() -> tuple[str, str]:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        org = Organization(id=org_id, name="NR Org", slug=f"nr-org-{org_id[:8]}")
        session.add(org)
        await session.commit()
        project = Project(
            id=proj_id,
            organization_id=org_id,
            name="NR Project",
            code="NRP",
        )
        session.add(project)
        await session.commit()
    return org_id, proj_id


async def _register_and_login(
    client: AsyncClient, email: str, username: str
) -> tuple[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "NR User",
            "password": "pass1234",
        },
    )
    user_id = reg.json()["id"]
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"], user_id


async def _add_membership(
    user_id: str, org_id: str, role: str = "member", is_org_admin: bool = False
) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id,
                organization_id=org_id,
                role_in_org=role,
                is_org_admin=is_org_admin,
            )
        )
        await session.commit()


# ─── GET (default rule) ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_naming_rule_returns_default(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr1@example.com", "nr1")
    await _add_membership(user_id, org_id)

    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_default"] is True
    assert data["separator"] == "-"
    assert len(data["segments"]) >= 5


# ─── PUT (create custom rule) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_naming_rule_creates_custom(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr2@example.com", "nr2")
    await _add_membership(user_id, org_id, role="org_admin", is_org_admin=True)

    rule_body = {
        "separator": "_",
        "segments": [
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    }
    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json=rule_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_default"] is False
    assert data["separator"] == "_"
    assert len(data["segments"]) == 2


# ─── GET returns custom rule after PUT ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_custom_after_put(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr3@example.com", "nr3")
    await _add_membership(user_id, org_id, role="org_admin", is_org_admin=True)

    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": ".",
            "segments": [{"key": "a", "label": "A", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["separator"] == "."
    assert res.json()["is_default"] is False


# ─── DELETE resets to default ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_naming_rule_resets_to_default(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr4@example.com", "nr4")
    await _add_membership(user_id, org_id, role="org_admin", is_org_admin=True)

    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [{"key": "x", "label": "X", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    del_res = await client.delete(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    get_res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.json()["is_default"] is True


# ─── Container creation auto-validates naming ─────────────────────────────────


@pytest.mark.asyncio
async def test_container_naming_valid_with_default_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr5@example.com", "nr5")
    await _add_membership(user_id, org_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001", "title": "Valid Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is True
    assert data["naming_issues"] is None


@pytest.mark.asyncio
async def test_container_naming_invalid_with_default_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr6@example.com", "nr6")
    await _add_membership(user_id, org_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "bad", "title": "Invalid Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is False
    assert data["naming_issues"] is not None


@pytest.mark.asyncio
async def test_container_uses_custom_naming_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr7@example.com", "nr7")
    await _add_membership(user_id, org_id, role="org_admin", is_org_admin=True)

    # Set simple custom rule: proj_code _ number
    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [
                {
                    "key": "proj",
                    "label": "Project",
                    "required": True,
                    "pattern": "^[A-Z]+$",
                },
                {
                    "key": "num",
                    "label": "Number",
                    "required": True,
                    "pattern": "^\\d+$",
                },
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    valid_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "ABC_001", "title": "Custom Rule Valid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert valid_res.status_code == 201
    assert valid_res.json()["naming_valid"] is True

    invalid_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "abc-001", "title": "Custom Rule Invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invalid_res.status_code == 201
    assert invalid_res.json()["naming_valid"] is False


# ─── Auth guards ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_naming_rule_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.get(f"/api/v1/projects/{proj_id}/naming-rules")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_put_naming_rule_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "-",
            "segments": [{"key": "a", "label": "A", "required": True}],
        },
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_delete_naming_rule_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.delete(f"/api/v1/projects/{proj_id}/naming-rules")
    assert res.status_code == 401


# ─── Non-member access (returns 404 to avoid info leakage) ───────────────────


@pytest.mark.asyncio
async def test_get_naming_rule_non_member_returns_404(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    token, _ = await _register_and_login(client, "nr8@example.com", "nr8")
    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_put_naming_rule_non_member_returns_404(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    token, _ = await _register_and_login(client, "nr9@example.com", "nr9")
    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [{"key": "a", "label": "A", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_naming_rule_non_member_returns_404(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    token, _ = await _register_and_login(client, "nr10@example.com", "nr10")
    res = await client.delete(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_naming_rule_unknown_project_returns_404(client: AsyncClient):
    token, _ = await _register_and_login(client, "nr11@example.com", "nr11")
    nonexistent = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/projects/{nonexistent}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


# ─── Platform admin bypass ────────────────────────────────────────────────────


async def _make_platform_admin(user_id: str) -> None:
    """Elevate user to platform admin via direct DB mutation (no API endpoint exists)."""
    from sqlalchemy import update

    from app.models.user import User
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_platform_admin=True)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_platform_admin_can_get_naming_rule_of_any_project(client: AsyncClient):
    """Platform admin bypasses org membership check and can read any project's naming rule."""
    _, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr_pa1@example.com", "nr_pa1")
    await _make_platform_admin(user_id)
    # Re-login so JWT reflects current state (explicit refresh for clarity)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "nr_pa1@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "segments" in res.json()


@pytest.mark.asyncio
async def test_platform_admin_can_put_naming_rule_of_any_project(client: AsyncClient):
    """Platform admin can set a custom naming rule for any project without org membership."""
    _, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr_pa2@example.com", "nr_pa2")
    await _make_platform_admin(user_id)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "nr_pa2@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [
                {"key": "proj", "label": "Project", "required": True},
                {"key": "seq", "label": "Sequence", "required": True},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_default"] is False
    assert res.json()["separator"] == "_"


@pytest.mark.asyncio
async def test_platform_admin_can_delete_naming_rule_of_any_project(
    client: AsyncClient,
):
    """Platform admin can reset any project's naming rule to default without org membership."""
    _, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr_pa3@example.com", "nr_pa3")
    await _make_platform_admin(user_id)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "nr_pa3@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    # First set a custom rule so DELETE has something to remove
    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": ".",
            "segments": [{"key": "x", "label": "X", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.delete(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204
