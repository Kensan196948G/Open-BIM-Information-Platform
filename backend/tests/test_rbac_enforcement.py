"""Endpoint-level RBAC enforcement tests (Issue #36)."""

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
        session.add(Organization(id=org_id, name="RBAC Org", slug=f"rbac-{org_id[:8]}"))
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="RBAC Project",
                code="RBAC",
            )
        )
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
            "full_name": "RBAC User",
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


async def _add_membership(user_id: str, org_id: str, role: str = "member") -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id,
                organization_id=org_id,
                role_in_org=role,
            )
        )
        await session.commit()


async def _member_and_reviewer(client: AsyncClient, org_id: str) -> tuple[str, str]:
    member_token, member_id = await _register_and_login(
        client, "rbac_m@example.com", "rbacm"
    )
    reviewer_token, reviewer_id = await _register_and_login(
        client, "rbac_r@example.com", "rbacr"
    )
    await _add_membership(member_id, org_id, role="member")
    await _add_membership(reviewer_id, org_id, role="reviewer")
    return member_token, reviewer_token


async def _create_submitted_container(
    client: AsyncClient, token: str, proj_id: str
) -> str:
    created = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "RBAC-ORG-ZZ-GF-DR-AR-0001", "title": "RBAC Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    container_id = created.json()["id"]
    submitted = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submitted.status_code == 200
    return container_id


@pytest.mark.asyncio
async def test_member_cannot_approve_container(client: AsyncClient):
    """Separation of duties: member must not publish/approve (403)."""
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    container_id = await _create_submitted_container(client, member_token, proj_id)

    denied = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert denied.status_code == 403

    approved = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert approved.status_code == 200
    assert approved.json()["current_state"] == "Published"


@pytest.mark.asyncio
async def test_member_cannot_archive_container(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    container_id = await _create_submitted_container(client, member_token, proj_id)

    denied = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "archive"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert denied.status_code == 403

    archived = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "archive"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert archived.status_code == 200


@pytest.mark.asyncio
async def test_member_can_create_update_submit(client: AsyncClient):
    """Member retains authoring permissions (create/update/submit)."""
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    container_id = await _create_submitted_container(client, member_token, proj_id)
    # WIP update requires moving back to WIP first; create a new WIP container.
    created = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "RBAC-ORG-ZZ-GF-DR-AR-0002", "title": "WIP Container"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert created.status_code == 201
    updated = await client.patch(
        f"/api/v1/projects/{proj_id}/containers/{created.json()['id']}",
        json={"title": "Updated by member"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert updated.status_code == 200
    assert container_id


@pytest.mark.asyncio
async def test_member_cannot_manage_naming_rules(client: AsyncClient):
    """Naming-rule management requires organization admin."""
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [{"key": "a", "label": "A", "required": True}],
        },
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 403


@pytest.mark.no_db
def test_default_role_matrix_has_separation_of_duties():
    from app.services.rbac import MEMBER_PERMISSIONS, REVIEWER_PERMISSIONS

    assert "container.approve" not in MEMBER_PERMISSIONS
    assert "container.archive" not in MEMBER_PERMISSIONS
    assert "container.approve" in REVIEWER_PERMISSIONS
    assert "container.archive" in REVIEWER_PERMISSIONS
