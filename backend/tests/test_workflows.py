"""Workflow and approval endpoint tests."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization

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


# ─── Full approval flow integration tests ──────────────────────────────────────


async def _create_container(client: AsyncClient, token: str, project_id: str) -> str:
    """Create a container and return its id."""
    res = await client.post(
        f"/api/v1/projects/{project_id}/containers",
        json={"identifier": "PRJ-ORG-ZZ-GF-DR-AR-0001", "title": "Test Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_full_approval_flow_approve(client: AsyncClient):
    """Member creates container, starts workflow, approves → workflow completed."""
    token, user_id = await _register_and_login(client, "appr@example.com", "appruser")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    container_id = await _create_container(client, token, project_id)

    # Start workflow with self as the single approver
    wf_res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": project_id,
            "target_type": "container",
            "target_id": container_id,
            "assignee_ids": [user_id],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wf_res.status_code == 201, wf_res.text
    workflow_id = wf_res.json()["id"]

    # Fetch the approval id
    from sqlalchemy import select

    from app.models.workflow import Approval
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Approval).where(Approval.workflow_id == workflow_id)
        )
        approval = result.scalar_one()
        approval_id = approval.id

    # Approve
    act_res = await client.post(
        f"/api/v1/workflows/{workflow_id}/approvals/{approval_id}/act",
        json={"result": "approved", "comment": "LGTM"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert act_res.status_code == 200, act_res.text
    assert act_res.json()["result"] == "approved"

    # Workflow should now be completed
    wf_get = await client.get(
        f"/api/v1/workflows/{workflow_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wf_get.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_double_act_returns_409(client: AsyncClient):
    """Acting twice on the same approval returns 409 Conflict."""
    token, user_id = await _register_and_login(client, "dbl@example.com", "dbluser")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)
    container_id = await _create_container(client, token, project_id)

    wf_res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": project_id,
            "target_type": "container",
            "target_id": container_id,
            "assignee_ids": [user_id],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = wf_res.json()["id"]

    from sqlalchemy import select

    from app.models.workflow import Approval
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Approval).where(Approval.workflow_id == workflow_id)
        )
        approval_id = result.scalar_one().id

    headers = {"Authorization": f"Bearer {token}"}
    first = await client.post(
        f"/api/v1/workflows/{workflow_id}/approvals/{approval_id}/act",
        json={"result": "approved"},
        headers=headers,
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/workflows/{workflow_id}/approvals/{approval_id}/act",
        json={"result": "approved"},
        headers=headers,
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_workflow_rejects_invalid_assignee(client: AsyncClient):
    """Assignee not in the project's org is rejected with 400."""
    token, user_id = await _register_and_login(client, "inv@example.com", "invuser")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)
    container_id = await _create_container(client, token, project_id)

    res = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": project_id,
            "target_type": "container",
            "target_id": container_id,
            "assignee_ids": [str(uuid.uuid4())],  # not a member
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_transition_target_state_mismatch(client: AsyncClient):
    """Container transition with wrong target_state returns 409."""
    token, user_id = await _register_and_login(client, "ts@example.com", "tsuser")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)
    container_id = await _create_container(client, token, project_id)

    # WIP + submit → Shared; but claim target_state=Published (mismatch)
    res = await client.post(
        f"/api/v1/projects/{project_id}/containers/{container_id}/transition",
        json={"action": "submit", "target_state": "Published"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_transition_wip_to_shared(client: AsyncClient):
    """Valid WIP → Shared transition succeeds."""
    token, user_id = await _register_and_login(client, "tr@example.com", "truser")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)
    container_id = await _create_container(client, token, project_id)

    res = await client.post(
        f"/api/v1/projects/{project_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "Shared"
