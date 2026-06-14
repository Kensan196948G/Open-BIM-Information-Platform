"""RBAC API integration tests."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.role import Permission, Role
from app.models.user import UserOrganization


async def _register_login(
    client: AsyncClient, email: str, username: str
) -> tuple[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "User",
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


async def _make_platform_admin(user_id: str) -> None:
    from app.models.user import User
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        result = await session.get(User, user_id)
        result.is_platform_admin = True
        await session.commit()


async def _create_org(name: str) -> str:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(Organization(id=org_id, name=name, slug=f"slug-{org_id[:8]}"))
        await session.commit()
    return org_id


async def _add_member(user_id: str, org_id: str, is_admin: bool = False) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id,
                organization_id=org_id,
                role_in_org="admin" if is_admin else "member",
                is_org_admin=is_admin,
            )
        )
        await session.commit()


async def _seed_permission(code: str, category: str = "general") -> str:
    from tests.conftest import TestSessionLocal

    perm_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(Permission(id=perm_id, code=code, category=category))
        await session.commit()
    return perm_id


async def _seed_role(org_id: str, name: str, is_system: bool = False) -> str:
    from tests.conftest import TestSessionLocal

    role_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(
            Role(
                id=role_id, organization_id=org_id, name=name, is_system_role=is_system
            )
        )
        await session.commit()
    return role_id


# ─── Permissions ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_permissions_requires_auth(client: AsyncClient):
    res = await client.get("/api/v1/permissions")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_permissions_authenticated(client: AsyncClient):
    await _seed_permission("project:read")
    token, _ = await _register_login(client, "perm1@example.com", "perm1user")
    res = await client.get(
        "/api/v1/permissions", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert any(p["code"] == "project:read" for p in res.json())


@pytest.mark.asyncio
async def test_create_permission_requires_platform_admin(client: AsyncClient):
    token, _ = await _register_login(client, "perm2@example.com", "perm2user")
    res = await client.post(
        "/api/v1/permissions",
        json={"code": "project:write", "category": "project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_permission_platform_admin_succeeds(client: AsyncClient):
    token, user_id = await _register_login(client, "perm3@example.com", "perm3user")
    await _make_platform_admin(user_id)
    res = await client.post(
        "/api/v1/permissions",
        json={
            "code": "org:admin",
            "category": "organization",
            "description": "Org admin",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "org:admin"
    assert data["category"] == "organization"


@pytest.mark.asyncio
async def test_create_permission_duplicate_code_returns_409(client: AsyncClient):
    token, user_id = await _register_login(client, "perm4@example.com", "perm4user")
    await _make_platform_admin(user_id)
    await _seed_permission("duplicate:code")
    res = await client.post(
        "/api/v1/permissions",
        json={"code": "duplicate:code", "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


# ─── Roles ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_roles_non_member_returns_404(client: AsyncClient):
    token, _ = await _register_login(client, "role1@example.com", "role1user")
    org_id = await _create_org("RoleOrg1")
    res = await client.get(
        f"/api/v1/organizations/{org_id}/roles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_roles_member_can_view(client: AsyncClient):
    token, user_id = await _register_login(client, "role2@example.com", "role2user")
    org_id = await _create_org("RoleOrg2")
    await _add_member(user_id, org_id)
    await _seed_role(org_id, "Viewer")

    res = await client.get(
        f"/api/v1/organizations/{org_id}/roles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    names = [r["name"] for r in res.json()]
    assert "Viewer" in names


@pytest.mark.asyncio
async def test_create_role_requires_org_admin(client: AsyncClient):
    token, user_id = await _register_login(client, "role3@example.com", "role3user")
    org_id = await _create_org("RoleOrg3")
    await _add_member(user_id, org_id, is_admin=False)

    res = await client.post(
        f"/api/v1/organizations/{org_id}/roles",
        json={"name": "Editor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_role_org_admin_succeeds(client: AsyncClient):
    token, user_id = await _register_login(client, "role4@example.com", "role4user")
    org_id = await _create_org("RoleOrg4")
    await _add_member(user_id, org_id, is_admin=True)

    res = await client.post(
        f"/api/v1/organizations/{org_id}/roles",
        json={"name": "Editor", "description": "Can edit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Editor"
    assert data["organization_id"] == org_id
    assert data["is_system_role"] is False
    assert data["permissions"] == []


@pytest.mark.asyncio
async def test_get_role(client: AsyncClient):
    token, user_id = await _register_login(client, "role5@example.com", "role5user")
    org_id = await _create_org("RoleOrg5")
    await _add_member(user_id, org_id)
    role_id = await _seed_role(org_id, "ReadOnly")

    res = await client.get(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "ReadOnly"


@pytest.mark.asyncio
async def test_update_role_org_admin(client: AsyncClient):
    token, user_id = await _register_login(client, "role6@example.com", "role6user")
    org_id = await _create_org("RoleOrg6")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "OldName")

    res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"name": "NewName"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "NewName"


@pytest.mark.asyncio
async def test_update_system_role_forbidden(client: AsyncClient):
    token, user_id = await _register_login(client, "role7@example.com", "role7user")
    org_id = await _create_org("RoleOrg7")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "SystemRole", is_system=True)

    res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_delete_role_org_admin(client: AsyncClient):
    token, user_id = await _register_login(client, "role8@example.com", "role8user")
    org_id = await _create_org("RoleOrg8")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "ToDelete")

    del_res = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    get_res = await client.get(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_system_role_forbidden(client: AsyncClient):
    token, user_id = await _register_login(client, "role9@example.com", "role9user")
    org_id = await _create_org("RoleOrg9")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "SysProtected", is_system=True)

    res = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


# ─── Role ↔ Permission ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_and_revoke_permission(client: AsyncClient):
    token, user_id = await _register_login(client, "rp1@example.com", "rp1user")
    org_id = await _create_org("RPOrg1")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "RPRole")
    perm_id = await _seed_permission("file:upload")

    assign_res = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": perm_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert assign_res.status_code == 201
    perms = assign_res.json()["permissions"]
    assert any(p["id"] == perm_id for p in perms)

    # idempotent — assigning again returns 201 without duplicate
    assign_res2 = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": perm_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert assign_res2.status_code == 201
    assert len(assign_res2.json()["permissions"]) == 1

    revoke_res = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_res.status_code == 204


@pytest.mark.asyncio
async def test_assign_unknown_permission_returns_404(client: AsyncClient):
    token, user_id = await _register_login(client, "rp2@example.com", "rp2user")
    org_id = await _create_org("RPOrg2")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "RPRole2")

    res = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_revoke_unassigned_permission_returns_404(client: AsyncClient):
    token, user_id = await _register_login(client, "rp3@example.com", "rp3user")
    org_id = await _create_org("RPOrg3")
    await _add_member(user_id, org_id, is_admin=True)
    role_id = await _seed_role(org_id, "RPRole3")
    perm_id = await _seed_permission("file:delete")

    res = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
