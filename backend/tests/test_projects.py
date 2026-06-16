"""Tests for /projects endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.user import UserOrganization

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _create_org(name: str = "Test Org") -> str:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        org = Organization(id=org_id, name=name, slug=f"torg-{org_id[:8]}")
        session.add(org)
        await session.commit()
    return org_id


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


async def _add_membership(user_id: str, org_id: str) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id, organization_id=org_id, role_in_org="member"
            )
        )
        await session.commit()


async def _setup(client: AsyncClient, suffix: str = "0") -> tuple[str, str]:
    """Create org + user + membership. Returns (token, org_id)."""
    org_id = await _create_org(f"Org {suffix}")
    token, user_id = await _register_and_login(
        client, f"pj{suffix}@example.com", f"pjuser{suffix}"
    )
    await _add_membership(user_id, org_id)
    return token, org_id


async def _create_project(
    client: AsyncClient,
    token: str,
    name: str = "Test Project",
    code: str = "TP-001",
) -> dict:
    return await client.post(
        "/api/v1/projects",
        json={"name": name, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )


# ─── List projects ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_projects_empty(client: AsyncClient):
    """New member with no projects sees empty list."""
    token, _ = await _setup(client, "1")
    res = await client.get(
        "/api/v1/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_projects_returns_created(client: AsyncClient):
    """After creating a project it appears in the list."""
    token, _ = await _setup(client, "2")
    await _create_project(client, token)
    res = await client.get(
        "/api/v1/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Test Project"


@pytest.mark.asyncio
async def test_list_projects_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    res = await client.get("/api/v1/projects")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_projects_pagination(client: AsyncClient):
    """Pagination parameters are respected."""
    token, _ = await _setup(client, "3")
    for i in range(3):
        await _create_project(client, token, f"Project {i}", f"P{i:03d}")
    res = await client.get(
        "/api/v1/projects",
        params={"page": 1, "size": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_projects_member_isolation(client: AsyncClient):
    """User only sees projects in their own organization."""
    token_a, _ = await _setup(client, "4a")
    token_b, _ = await _setup(client, "4b")  # different org
    await _create_project(client, token_a, "Org A Project", "OA-001")
    res = await client.get(
        "/api/v1/projects", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ─── Create project ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_success(client: AsyncClient):
    """Member can create a project."""
    token, _ = await _setup(client, "5")
    res = await _create_project(client, token, "New BIM Project", "BIM-001")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "New BIM Project"
    assert data["code"] == "BIM-001"
    assert data["status"] == "active"
    assert data["applied_standard"] == "ISO 19650"
    assert "id" in data
    assert "organization_id" in data


@pytest.mark.asyncio
async def test_create_project_requires_auth(client: AsyncClient):
    """Unauthenticated create returns 401."""
    res = await client.post("/api/v1/projects", json={"name": "Ghost", "code": "G-001"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_project_no_membership_returns_403(client: AsyncClient):
    """User without org membership cannot create projects."""
    token, _ = await _register_and_login(client, "nomem@example.com", "nomemuser")
    res = await client.post(
        "/api/v1/projects",
        json={"name": "Orphan", "code": "OR-001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_project_with_optional_fields(client: AsyncClient):
    """Project can be created with description and dates."""
    token, _ = await _setup(client, "6")
    res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Full Project",
            "code": "FP-001",
            "description": "A detailed project",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["description"] == "A detailed project"
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-12-31"


# ─── Get project ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_project_success(client: AsyncClient):
    """Member can retrieve a specific project by ID."""
    token, _ = await _setup(client, "7")
    create_res = await _create_project(client, token)
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    res = await client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == project_id
    assert data["name"] == "Test Project"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    """Unknown project ID returns 404."""
    token, _ = await _setup(client, "8")
    res = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_project_non_member_returns_404(client: AsyncClient):
    """Non-member cannot see project — returns 404 (security by obscurity)."""
    token_a, _ = await _setup(client, "9a")
    token_b, _ = await _setup(client, "9b")
    project_id = (await _create_project(client, token_a)).json()["id"]

    res = await client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_project_requires_auth(client: AsyncClient):
    """Unauthenticated get returns 401."""
    token, _ = await _setup(client, "10")
    project_id = (await _create_project(client, token)).json()["id"]
    res = await client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 401


# ─── Update project ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_project_name(client: AsyncClient):
    """PATCH updates the project name."""
    token, _ = await _setup(client, "11")
    project_id = (await _create_project(client, token)).json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed Project"


@pytest.mark.asyncio
async def test_update_project_status(client: AsyncClient):
    """PATCH can change project status."""
    token, _ = await _setup(client, "12")
    project_id = (await _create_project(client, token)).json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "archived"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_update_project_partial(client: AsyncClient):
    """PATCH is partial — unspecified fields are unchanged."""
    token, _ = await _setup(client, "13")
    project_id = (await _create_project(client, token, code="PC-001")).json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "Updated desc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["description"] == "Updated desc"
    assert data["code"] == "PC-001"  # unchanged


@pytest.mark.asyncio
async def test_update_project_not_found(client: AsyncClient):
    """PATCH on unknown project returns 404."""
    token, _ = await _setup(client, "14")
    res = await client.patch(
        f"/api/v1/projects/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_project_non_member_returns_404(client: AsyncClient):
    """Non-member PATCH returns 404."""
    token_a, _ = await _setup(client, "15a")
    token_b, _ = await _setup(client, "15b")
    project_id = (await _create_project(client, token_a)).json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Stolen"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_project_requires_auth(client: AsyncClient):
    """Unauthenticated PATCH returns 401."""
    token, _ = await _setup(client, "16")
    project_id = (await _create_project(client, token)).json()["id"]
    res = await client.patch(f"/api/v1/projects/{project_id}", json={"name": "Ghost"})
    assert res.status_code == 401


# ─── Platform admin paths ─────────────────────────────────────────────────────


async def _make_platform_admin(user_id: str) -> None:
    """Elevate an existing user to platform admin via direct DB write."""
    from sqlalchemy import update

    from app.models.user import User
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_platform_admin=True)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_platform_admin_lists_all_projects(client: AsyncClient):
    """Platform admin sees projects across all organizations."""
    # Two independent orgs each with one project
    token_a, _ = await _setup(client, "pa1a")
    token_b, _ = await _setup(client, "pa1b")
    await _create_project(client, token_a, name="Org A Project", code="OA-001")
    await _create_project(client, token_b, name="Org B Project", code="OB-001")

    # Create a third user who is a platform admin (no org membership)
    _, admin_id = await _register_and_login(
        client, "admin_list@example.com", "adminlist"
    )
    await _make_platform_admin(admin_id)
    # Re-login to get fresh token reflecting admin status
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin_list@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    admin_token = res.json()["access_token"]

    resp = await client.get(
        "/api/v1/projects", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_platform_admin_can_get_any_project(client: AsyncClient):
    """Platform admin can GET a project without being a member."""
    token, _ = await _setup(client, "pa2")
    project_id = (await _create_project(client, token, code="PA-002")).json()["id"]

    _, admin_id = await _register_and_login(
        client, "admin_get@example.com", "admingett"
    )
    await _make_platform_admin(admin_id)
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin_get@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    admin_token = res.json()["access_token"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


@pytest.mark.asyncio
async def test_platform_admin_create_project_without_org_returns_400(
    client: AsyncClient,
):
    """Platform admin who is not in any org cannot create project (must specify org_id)."""
    _, admin_id = await _register_and_login(
        client, "admin_create@example.com", "admincreate"
    )
    await _make_platform_admin(admin_id)
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin_create@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    admin_token = res.json()["access_token"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Admin Project", "code": "AP-001"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "organization_id" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_platform_admin_can_patch_any_project(client: AsyncClient):
    """Platform admin can PATCH a project without being a member of its org."""
    token, _ = await _setup(client, "pa4")
    project_id = (await _create_project(client, token, code="PA-004")).json()["id"]

    _, admin_id = await _register_and_login(
        client, "admin_patch@example.com", "adminpatch"
    )
    await _make_platform_admin(admin_id)
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin_patch@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    admin_token = res.json()["access_token"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Admin Renamed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Admin Renamed"
