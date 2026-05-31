"""Workflow and approval endpoint tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User, UserOrganization


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _setup_org_project() -> tuple[str, str]:
    """Create org + project with unique IDs, return (org_id, project_id)."""
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        org = Organization(id=org_id, name="Test Org", slug=f"test-org-{org_id[:8]}")
        session.add(org)
        await session.commit()
        project = Project(
            id=proj_id,
            organization_id=org_id,
            name="Test Project",
            code="TP-001",
        )
        session.add(project)
        await session.commit()
    return org_id, proj_id


async def _register_and_login(
    client: AsyncClient,
    email: str = "wf@example.com",
    username: str = "wfuser",
) -> tuple[str, str]:
    """Register user, login, return (token, user_id)."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "WF User",
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


async def _add_membership(user_id: str, org_id: str) -> None:
    """Add user to organization."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        membership = UserOrganization(
            user_id=user_id,
            organization_id=org_id,
            role_in_org="member",
        )
        session.add(membership)
        await session.commit()


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_workflow_requires_membership(client: AsyncClient):
    """User not in org cannot start workflow."""
    token, _ = await _register_and_login(client, "wf1@example.com", "wfuser1")
    _, project_id = await _setup_org_project()

    res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": project_id,
            "target_type": "container",
            "target_id": str(uuid.uuid4()),
            "workflow_type": "state_transition",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_start_workflow_nonexistent_project(client: AsyncClient):
    """Request with unknown project_id returns 404."""
    token, _ = await _register_and_login(client, "wf2@example.com", "wfuser2")

    res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": str(uuid.uuid4()),
            "target_type": "container",
            "target_id": str(uuid.uuid4()),
            "workflow_type": "state_transition",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_naming_validate_compliant(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv@example.com", "nvuser")

    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is True
    assert res.json()["level"] == "compliant"


@pytest.mark.asyncio
async def test_naming_validate_non_compliant(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv2@example.com", "nvuser2")

    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "INVALID"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is False
    assert len(res.json()["issues"]) > 0


@pytest.mark.asyncio
async def test_naming_validate_requires_auth(client: AsyncClient):
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001"},
    )
    # HTTPBearer returns 401 when no Authorization header is present
    assert res.status_code == 401
