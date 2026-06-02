"""Tests for project naming rules API (Issue #3)."""

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
        org = Organization(id=org_id, name="NR Org", slug=f"nr-org-{org_id[:8]}")
        session.add(org)
        await session.commit()
        project = Project(
            id=proj_id,
            organization_id=org_id,
            name="NR Project",
            code="NRP",
        )
        session.add(project)
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
            "full_name": "NR User",
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
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(UserOrganization(user_id=user_id, organization_id=org_id))
        await session.commit()


# ─── GET (default rule) ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_naming_rule_returns_default(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr1@example.com", "nr1")
    await _add_membership(user_id, org_id)

    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_default"] is True
    assert data["separator"] == "-"
    assert len(data["segments"]) >= 5


# ─── PUT (create custom rule) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_naming_rule_creates_custom(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr2@example.com", "nr2")
    await _add_membership(user_id, org_id)

    rule_body = {
        "separator": "_",
        "segments": [
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    }
    res = await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json=rule_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_default"] is False
    assert data["separator"] == "_"
    assert len(data["segments"]) == 2


# ─── GET returns custom rule after PUT ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_custom_after_put(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr3@example.com", "nr3")
    await _add_membership(user_id, org_id)

    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": ".",
            "segments": [{"key": "a", "label": "A", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["separator"] == "."
    assert res.json()["is_default"] is False


# ─── DELETE resets to default ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_naming_rule_resets_to_default(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr4@example.com", "nr4")
    await _add_membership(user_id, org_id)

    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [{"key": "x", "label": "X", "required": True}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    del_res = await client.delete(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    get_res = await client.get(
        f"/api/v1/projects/{proj_id}/naming-rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.json()["is_default"] is True


# ─── Container creation auto-validates naming ─────────────────────────────────


@pytest.mark.asyncio
async def test_container_naming_valid_with_default_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr5@example.com", "nr5")
    await _add_membership(user_id, org_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001", "title": "Valid Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is True
    assert data["naming_issues"] is None


@pytest.mark.asyncio
async def test_container_naming_invalid_with_default_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr6@example.com", "nr6")
    await _add_membership(user_id, org_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "bad", "title": "Invalid Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is False
    assert data["naming_issues"] is not None


@pytest.mark.asyncio
async def test_container_uses_custom_naming_rule(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nr7@example.com", "nr7")
    await _add_membership(user_id, org_id)

    # Set simple custom rule: proj_code _ number
    await client.put(
        f"/api/v1/projects/{proj_id}/naming-rules",
        json={
            "separator": "_",
            "segments": [
                {
                    "key": "proj",
                    "label": "Project",
                    "required": True,
                    "pattern": "^[A-Z]+$",
                },
                {
                    "key": "num",
                    "label": "Number",
                    "required": True,
                    "pattern": "^\\d+$",
                },
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    valid_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "ABC_001", "title": "Custom Rule Valid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert valid_res.status_code == 201
    assert valid_res.json()["naming_valid"] is True

    invalid_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "abc-001", "title": "Custom Rule Invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invalid_res.status_code == 201
    assert invalid_res.json()["naming_valid"] is False
