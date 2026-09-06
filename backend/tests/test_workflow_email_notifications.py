"""Integration tests: workflow/container notifications also queue email
(Issue #53). ``send_mail_safe`` is monkeypatched at the call-site import so
these tests never touch a real network/SMTP server, matching CI's
SMTP_ENABLED=False default in production code paths.
"""

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
        session.add(Organization(id=org_id, name="Mail Org", slug=f"mail-{org_id[:8]}"))
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="Mail Project",
                code="MAL",
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
            "full_name": "Mail User",
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
            UserOrganization(user_id=user_id, organization_id=org_id, role_in_org=role)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_workflow_assignment_and_result_queue_email(
    client: AsyncClient, monkeypatch
):
    """workflow start (assignment) and act (result) each queue a background
    send_mail_safe call addressed to the correct recipient's registered
    email — without requiring a real SMTP server."""
    sent: list[dict] = []

    def _fake_send_mail_safe(*, to_email: str, subject: str, body: str) -> None:
        sent.append({"to_email": to_email, "subject": subject, "body": body})

    monkeypatch.setattr("app.api.v1.workflows.send_mail_safe", _fake_send_mail_safe)

    org_id, proj_id = await _setup_org_project()
    initiator_token, initiator_id = await _register_and_login(
        client, "mail_i@example.com", "maili"
    )
    approver_token, approver_id = await _register_and_login(
        client, "mail_a@example.com", "maila"
    )
    await _add_membership(initiator_id, org_id)
    await _add_membership(approver_id, org_id)

    created = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "MAL-ORG-ZZ-GF-DR-AR-0001", "title": "Mail Container"},
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

    # Assignment email sent to the approver's registered address.
    assert len(sent) == 1
    assert sent[0]["to_email"] == "mail_a@example.com"
    assert sent[0]["subject"] == "承認依頼が届きました"

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

    # Result email sent to the initiator's registered address.
    assert len(sent) == 2
    assert sent[1]["to_email"] == "mail_i@example.com"
    assert sent[1]["subject"] == "承認結果の通知"


@pytest.mark.asyncio
async def test_container_transition_queues_email_on_return(
    client: AsyncClient, monkeypatch
):
    """A container 'return' transition queues an email to the container's
    creator via the same send_mail_safe background-task path."""
    sent: list[dict] = []

    def _fake_send_mail_safe(*, to_email: str, subject: str, body: str) -> None:
        sent.append({"to_email": to_email, "subject": subject, "body": body})

    monkeypatch.setattr("app.api.v1.containers.send_mail_safe", _fake_send_mail_safe)
    monkeypatch.setattr("app.api.v1.workflows.send_mail_safe", _fake_send_mail_safe)

    org_id, proj_id = await _setup_org_project()
    creator_token, creator_id = await _register_and_login(
        client, "mail_c@example.com", "mailc"
    )
    approver_token, approver_id = await _register_and_login(
        client, "mail_r@example.com", "mailr"
    )
    await _add_membership(creator_id, org_id)
    await _add_membership(approver_id, org_id, role="reviewer")

    created = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "MAL-ORG-ZZ-GF-DR-AR-0002", "title": "Return Container"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert created.status_code == 201
    container_id = created.json()["id"]

    submitted = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert submitted.status_code == 200

    returned = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "return", "comment": "needs work"},
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert returned.status_code == 200

    assert any(
        item["to_email"] == "mail_c@example.com"
        and "コンテナ状態が変更されました" in item["subject"]
        for item in sent
    )
