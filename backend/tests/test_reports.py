"""Audit & compliance reports API tests (Issue #51)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization
from app.models.workflow import WorkflowInstance, WorkflowStatus, WorkflowTask

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _setup_org_project() -> tuple[str, str]:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(
            Organization(id=org_id, name="Report Org", slug=f"rep-org-{org_id[:8]}")
        )
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="Report Project",
                code="REP-001",
            )
        )
        await session.commit()
    return org_id, proj_id


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


async def _add_membership(
    user_id: str, org_id: str, role_in_org: str = "member"
) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id, organization_id=org_id, role_in_org=role_in_org
            )
        )
        await session.commit()


async def _create_container(
    client: AsyncClient, token: str, project_id: str, identifier: str, title: str
) -> str:
    res = await client.post(
        f"/api/v1/projects/{project_id}/containers",
        json={"identifier": identifier, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ─── naming-violations ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_naming_violations_reports_non_compliant_container(
    client: AsyncClient,
):
    """A container that failed naming validation is reported."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "nv1@example.com", "nvuser1")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    container_id = await _create_container(
        client, token, project_id, "NOT-A-VALID-ID", "Bad Naming Container"
    )

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/naming-violations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 1
    matches = [i for i in data["items"] if i["container_id"] == container_id]
    assert len(matches) == 1
    item = matches[0]
    assert item["violation_type"] == "naming_non_compliant"
    assert item["identifier"] == "NOT-A-VALID-ID"
    assert item["current_assignee_id"] == user_id
    assert item["reason"]


@pytest.mark.asyncio
async def test_naming_violations_reports_rejected_container(client: AsyncClient):
    """A container reverted to WIP via workflow rejection is reported."""
    from sqlalchemy import select

    from app.models.workflow import Approval
    from tests.conftest import TestSessionLocal

    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "nv2@example.com", "nvuser2")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    container_id = await _create_container(
        client, token, project_id, "PRJ-ORG-ZZ-GF-DR-AR-0001", "Rejected Container"
    )

    trans = await client.post(
        f"/api/v1/projects/{project_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert trans.status_code == 200

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
    assert wf_res.status_code == 201
    workflow_id = wf_res.json()["id"]

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Approval).where(Approval.workflow_id == workflow_id)
        )
        approval_id = result.scalar_one().id

    reject_res = await client.post(
        f"/api/v1/workflows/{workflow_id}/approvals/{approval_id}/act",
        json={"result": "rejected", "comment": "命名規則違反のため差戻し"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reject_res.status_code == 200

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/naming-violations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    matches = [
        i
        for i in data["items"]
        if i["container_id"] == container_id and i["violation_type"] == "rejected"
    ]
    assert len(matches) == 1
    item = matches[0]
    assert item["reason"] == "命名規則違反のため差戻し"
    assert item["occurred_at"]
    assert item["current_state"] == "WIP"


@pytest.mark.asyncio
async def test_naming_violations_empty_project(client: AsyncClient):
    """A project with no containers reports an empty list."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "nv3@example.com", "nvuser3")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/naming-violations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_naming_violations_member_forbidden(client: AsyncClient):
    """Plain members (not reviewer/org_admin) cannot access reports."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "nv4@example.com", "nvuser4")
    await _add_membership(user_id, org_id, role_in_org="member")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/naming-violations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


# ─── approval-delays ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approval_delays_reports_pending_over_threshold(client: AsyncClient):
    """A pending workflow older than threshold_hours is reported."""
    from tests.conftest import TestSessionLocal

    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "ad1@example.com", "aduser1")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    container_id = await _create_container(
        client, token, project_id, "PRJ-ORG-ZZ-GF-DR-AR-0002", "Delayed Container"
    )

    old_workflow_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        workflow = WorkflowInstance(
            id=old_workflow_id,
            project_id=project_id,
            target_type="container",
            target_id=container_id,
            workflow_type="state_transition",
            status=WorkflowStatus.pending,
            initiated_by=user_id,
            created_at=datetime.now(UTC) - timedelta(hours=100),
        )
        session.add(workflow)
        session.add(
            WorkflowTask(
                id=str(uuid.uuid4()),
                workflow_id=old_workflow_id,
                assignee_id=user_id,
                task_type="review",
                status=WorkflowStatus.pending,
                order=0,
            )
        )
        await session.commit()

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/approval-delays",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["threshold_hours"] == 72.0
    matches = [i for i in data["items"] if i["workflow_id"] == old_workflow_id]
    assert len(matches) == 1
    item = matches[0]
    assert item["container_identifier"] == "PRJ-ORG-ZZ-GF-DR-AR-0002"
    assert item["elapsed_hours"] >= 72.0
    assert item["assignees"][0]["assignee_id"] == user_id


@pytest.mark.asyncio
async def test_approval_delays_custom_threshold_excludes_recent(client: AsyncClient):
    """A pending workflow younger than threshold_hours is excluded."""
    from tests.conftest import TestSessionLocal

    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "ad2@example.com", "aduser2")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    container_id = await _create_container(
        client, token, project_id, "PRJ-ORG-ZZ-GF-DR-AR-0003", "Recent Container"
    )

    recent_workflow_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(
            WorkflowInstance(
                id=recent_workflow_id,
                project_id=project_id,
                target_type="container",
                target_id=container_id,
                workflow_type="state_transition",
                status=WorkflowStatus.pending,
                initiated_by=user_id,
                created_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await session.commit()

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/approval-delays",
        params={"threshold_hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["threshold_hours"] == 24.0
    assert all(i["workflow_id"] != recent_workflow_id for i in data["items"])


@pytest.mark.asyncio
async def test_approval_delays_empty_project(client: AsyncClient):
    """No pending workflows -> empty report."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "ad3@example.com", "aduser3")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/approval-delays",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_approval_delays_member_forbidden(client: AsyncClient):
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "ad4@example.com", "aduser4")
    await _add_membership(user_id, org_id, role_in_org="member")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/approval-delays",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


# ─── requirements-status ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_requirements_status_aggregates_item_counts(client: AsyncClient):
    """Per-document met/partial/not_met counts and fulfillment_rate are correct."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "rs1@example.com", "rsuser1")
    await _add_membership(user_id, org_id, role_in_org="reviewer")
    headers = {"Authorization": f"Bearer {token}"}

    doc_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "EIR", "title": "EIR Doc"},
        headers=headers,
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    for i, item_status in enumerate(["met", "met", "partial", "not_met"]):
        item_res = await client.post(
            f"/api/v1/projects/{project_id}/requirements/{doc_id}/items",
            json={
                "item_no": f"{i + 1:03d}",
                "what": f"Item {i}",
                "status": item_status,
            },
            headers=headers,
        )
        assert item_res.status_code == 201, item_res.text

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/requirements-status",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    matches = [i for i in data["items"] if i["document_id"] == doc_id]
    assert len(matches) == 1
    item = matches[0]
    assert item["met_count"] == 2
    assert item["partial_count"] == 1
    assert item["not_met_count"] == 1
    assert item["total_count"] == 4
    assert item["fulfillment_rate"] == 0.5


@pytest.mark.asyncio
async def test_requirements_status_document_with_no_items(client: AsyncClient):
    """A document with zero items reports fulfillment_rate 0.0."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "rs2@example.com", "rsuser2")
    await _add_membership(user_id, org_id, role_in_org="reviewer")
    headers = {"Authorization": f"Bearer {token}"}

    doc_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "BEP", "title": "Empty BEP"},
        headers=headers,
    )
    doc_id = doc_res.json()["id"]

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/requirements-status",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    matches = [i for i in data["items"] if i["document_id"] == doc_id]
    assert len(matches) == 1
    assert matches[0]["total_count"] == 0
    assert matches[0]["fulfillment_rate"] == 0.0


@pytest.mark.asyncio
async def test_requirements_status_empty_project(client: AsyncClient):
    """A project with no requirements documents reports an empty list."""
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "rs3@example.com", "rsuser3")
    await _add_membership(user_id, org_id, role_in_org="reviewer")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/requirements-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_requirements_status_member_forbidden(client: AsyncClient):
    org_id, project_id = await _setup_org_project()
    token, user_id = await _register_login(client, "rs4@example.com", "rsuser4")
    await _add_membership(user_id, org_id, role_in_org="member")

    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/requirements-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_naming_violations_requires_auth(client: AsyncClient):
    _, project_id = await _setup_org_project()
    res = await client.get(
        f"/api/v1/projects/{project_id}/reports/naming-violations",
    )
    assert res.status_code == 401
