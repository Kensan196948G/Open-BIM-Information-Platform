"""Audit writes — verify business operations create audit log entries."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization


async def _setup_org_project(db_session) -> tuple[str, str]:
    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with db_session() as session:
        session.add(
            Organization(id=org_id, name="Audit Org", slug=f"audit-{org_id[:8]}")
        )
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="Audit Project",
                code="AUD-001",
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
            "full_name": "Audit User",
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


async def _make_admin(db_session, user_id: str) -> None:
    from sqlalchemy import update

    from app.models.user import User

    async with db_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_platform_admin=True)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_container_transition_writes_audit(client: AsyncClient, db_session):
    token, user_id = await _register_login(client, "audit@example.com", "audituser")
    org_id, proj_id = await _setup_org_project(db_session)
    async with db_session() as session:
        session.add(
            UserOrganization(
                user_id=user_id, organization_id=org_id, role_in_org="member"
            )
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    create_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={
            "identifier": "AUD-ORG-ZZ-GF-DR-AR-0001",
            "title": "Audit Container",
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    container_id = create_res.json()["id"]

    transition_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit", "comment": "review please"},
        headers=headers,
    )
    assert transition_res.status_code == 200, transition_res.text

    await _make_admin(db_session, user_id)
    res = await client.get(
        "/api/v1/audit-logs",
        params={"target_type": "container", "target_id": container_id},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    event_types = [item["event_type"] for item in data["items"]]
    assert "container.created" in event_types
    assert "container.state_changed" in event_types
    state_item = next(
        i for i in data["items"] if i["event_type"] == "container.state_changed"
    )
    assert state_item["after_json"]["action"] == "submit"
    assert state_item["before_json"]["current_state"] == "WIP"
    assert state_item["after_json"]["current_state"] == "Shared"


@pytest.mark.asyncio
async def test_login_failure_writes_audit(client: AsyncClient, db_session):
    token, user_id = await _register_login(client, "fail@example.com", "failuser")
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "fail@example.com", "password": "wrongpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 401

    await _make_admin(db_session, user_id)
    res = await client.get(
        "/api/v1/audit-logs",
        params={"event_type": "user.login_failed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert all(item["result"] == "failure" for item in data["items"])
