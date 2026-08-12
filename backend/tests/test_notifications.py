"""In-app notification tests (Issue #34)."""

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
        session.add(
            Organization(id=org_id, name="Notif Org", slug=f"notif-{org_id[:8]}")
        )
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="Notif Project",
                code="NTF",
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
            "full_name": "Notif User",
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


async def _add_membership(user_id: str, org_id: str) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(UserOrganization(user_id=user_id, organization_id=org_id))
        await session.commit()


@pytest.mark.asyncio
async def test_workflow_start_and_act_create_notifications(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    initiator_token, initiator_id = await _register_and_login(
        client, "ntf_i@example.com", "ntfi"
    )
    approver_token, approver_id = await _register_and_login(
        client, "ntf_a@example.com", "ntfa"
    )
    await _add_membership(initiator_id, org_id)
    await _add_membership(approver_id, org_id)

    created = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "NTF-ORG-ZZ-GF-DR-AR-0001", "title": "Notif Container"},
        headers={"Authorization": f"Bearer {initiator_token}"},
    )
    assert created.status_code == 201
    container_id = created.json()["id"]

    wf = await client.post(
        "/api/v1/workflows",
        json={
            "project_id": proj_id,
            "target_type": "container",
            "target_id": container_id,
            "workflow_type": "state_transition",
            "assignee_ids": [approver_id],
        },
        headers={"Authorization": f"Bearer {initiator_token}"},
    )
    assert wf.status_code == 201

    # Approver receives an assignment notification.
    approver_notifs = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert approver_notifs.status_code == 200
    data = approver_notifs.json()
    assert data["unread_count"] == 1
    assert data["items"][0]["event_type"] == "workflow.assigned"

    # Act on the approval → initiator gets a result notification.
    tasks = await client.get(
        "/api/v1/workflows/tasks/mine",
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    task = tasks.json()[0]
    acted = await client.post(
        f"/api/v1/workflows/{task['workflow_id']}/approvals/{task['approval_id']}/act",
        json={"result": "approved", "comment": "ok"},
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert acted.status_code == 200

    initiator_notifs = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {initiator_token}"},
    )
    assert initiator_notifs.json()["unread_count"] == 1
    assert initiator_notifs.json()["items"][0]["event_type"] == "workflow.result"


@pytest.mark.asyncio
async def test_mark_read_and_read_all(client: AsyncClient):
    from app.models.notification import Notification
    from app.services.notifications import notify_user
    from tests.conftest import TestSessionLocal

    token, user_id = await _register_and_login(
        client, "ntf_mark@example.com", "ntfmark"
    )
    async with TestSessionLocal() as session:
        notify_user(
            session,
            user_id=user_id,
            event_type="test.event",
            title="Test notification",
        )
        notify_user(
            session,
            user_id=user_id,
            event_type="test.event2",
            title="Test notification 2",
        )
        await session.commit()

    listing = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["unread_count"] == 2

    first_id = listing.json()["items"][0]["id"]
    marked = await client.post(
        f"/api/v1/notifications/{first_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    unread = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unread.json()["total"] == 1

    await client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )
    after = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.json()["unread_count"] == 0
    assert Notification is not None


@pytest.mark.asyncio
async def test_notifications_are_user_scoped(client: AsyncClient):
    token_a, user_a = await _register_and_login(
        client, "ntf_scope_a@example.com", "ntfscopea"
    )
    token_b, _ = await _register_and_login(
        client, "ntf_scope_b@example.com", "ntfscopeb"
    )
    from app.models.notification import Notification
    from app.services.notifications import notify_user
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        notify_user(
            session,
            user_id=user_a,
            event_type="test.scope",
            title="Only for A",
        )
        await session.commit()

    b_list = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert b_list.json()["total"] == 0
    a_list = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert a_list.json()["total"] == 1
    assert Notification is not None
