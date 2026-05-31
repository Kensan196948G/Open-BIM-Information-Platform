"""Workflow and approval endpoint tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization

# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _setup_org_project(db) -> tuple[str, str]:
    """Create org + project and return (org_id, project_id)."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        org = Organization(id="org-1", name="Test Org", slug="test-org")
        session.add(org)
        await session.commit()
        project = Project(
            id="proj-1",
            organization_id="org-1",
            name="Test Project",
            code="TP-001",
        )
        session.add(project)
        await session.commit()
    return "org-1", "proj-1"


async def _register_and_login(client: AsyncClient, email: str = "wf@example.com") -> tuple[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": "wfuser", "full_name": "WF User", "password": "pass1234"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    data = res.json()
    return data["access_token"], data.get("user_id", "")


async def _add_membership(db, user_id: str, org_id: str):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        # fetch user id from DB
        from app.models.user import User

        result = await session.execute(select(User).where(User.email == "wf@example.com"))
        user = result.scalar_one_or_none()
        if user:
            membership = UserOrganization(
                user_id=user.id,
                organization_id=org_id,
                role_in_org="member",
            )
            session.add(membership)
            await session.commit()
            return user.id
    return None


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_workflow(client: AsyncClient):
    token, _ = await _register_and_login(client)
    org_id, project_id = await _setup_org_project(None)
    await _add_membership(None, "", org_id)

    res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": project_id,
            "target_type": "container",
            "target_id": "container-fake-id",
            "workflow_type": "state_transition",
            "comment": "Submitting for review",
            "assignee_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["project_id"] == project_id
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_start_workflow_wrong_project(client: AsyncClient):
    token, _ = await _register_and_login(client, "other@example.com")
    await _setup_org_project(None)

    res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": "nonexistent-project",
            "target_type": "container",
            "target_id": "fake",
            "workflow_type": "state_transition",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_naming_validate_compliant(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "nv@example.com", "username": "nvuser", "full_name": "NV", "password": "pass1234"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "nv@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = res.json()["access_token"]

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
    await client.post(
        "/api/v1/auth/register",
        json={"email": "nv2@example.com", "username": "nvuser2", "full_name": "NV2", "password": "pass1234"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "nv2@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = res.json()["access_token"]

    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "INVALID"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is False
    assert len(res.json()["issues"]) > 0
