"""Requirements Documents API integration tests."""

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
            Organization(id=org_id, name="Req Org", slug=f"req-org-{org_id[:8]}")
        )
        await session.commit()
        session.add(
            Project(
                id=proj_id, organization_id=org_id, name="Req Project", code="RP-001"
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


async def _add_membership(user_id: str, org_id: str) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        session.add(
            UserOrganization(
                user_id=user_id, organization_id=org_id, role_in_org="member"
            )
        )
        await session.commit()


# ─── Create ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_requirements_document(client: AsyncClient):
    """Member creates an EIR document — returns 201 with correct fields."""
    token, user_id = await _register_login(client, "rq1@example.com", "rquser1")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={
            "doc_type": "EIR",
            "title": "Employer's Information Requirements",
            "revision": "A",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["doc_type"] == "EIR"
    assert data["title"] == "Employer's Information Requirements"
    assert data["revision"] == "A"
    assert data["status"] == "draft"
    assert data["project_id"] == project_id
    assert data["owner_user_id"] == user_id


@pytest.mark.asyncio
async def test_create_requirements_non_member_returns_404(client: AsyncClient):
    """Non-member cannot create document — 404."""
    token, _ = await _register_login(client, "rq2@example.com", "rquser2")
    _, project_id = await _setup_org_project()

    res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "BEP", "title": "BIM Execution Plan"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_requirements_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    _, project_id = await _setup_org_project()
    res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "OIR", "title": "Org Info Req"},
    )
    assert res.status_code == 401


# ─── List ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_requirements_documents(client: AsyncClient):
    """Member lists documents — returns seeded entries."""
    token, user_id = await _register_login(client, "rq3@example.com", "rquser3")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "EIR", "title": "EIR Doc"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "BEP", "title": "BEP Doc"},
        headers=headers,
    )

    res = await client.get(
        f"/api/v1/projects/{project_id}/requirements",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_requirements_filter_doc_type(client: AsyncClient):
    """Filter by doc_type returns only matching documents."""
    token, user_id = await _register_login(client, "rq4@example.com", "rquser4")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    for dt in ["EIR", "BEP", "OIR"]:
        await client.post(
            f"/api/v1/projects/{project_id}/requirements",
            json={"doc_type": dt, "title": f"{dt} Doc"},
            headers=headers,
        )

    res = await client.get(
        f"/api/v1/projects/{project_id}/requirements",
        params={"doc_type": "EIR"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_type"] == "EIR"


# ─── Get / Update / Delete ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_requirements_document(client: AsyncClient):
    """GET by ID returns correct document."""
    token, user_id = await _register_login(client, "rq5@example.com", "rquser5")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    create_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "MIDP", "title": "Master Info Delivery Plan"},
        headers=headers,
    )
    doc_id = create_res.json()["id"]

    res = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["id"] == doc_id
    assert res.json()["doc_type"] == "MIDP"


@pytest.mark.asyncio
async def test_update_requirements_document(client: AsyncClient):
    """PATCH updates status and revision."""
    token, user_id = await _register_login(client, "rq6@example.com", "rquser6")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    create_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "BEP", "title": "BIM Execution Plan"},
        headers=headers,
    )
    doc_id = create_res.json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}",
        json={"status": "approved", "revision": "B"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
    assert res.json()["revision"] == "B"


@pytest.mark.asyncio
async def test_delete_requirements_document(client: AsyncClient):
    """DELETE removes document — subsequent GET returns 404."""
    token, user_id = await _register_login(client, "rq7@example.com", "rquser7")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    create_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "OIR", "title": "Org Info Req"},
        headers=headers,
    )
    doc_id = create_res.json()["id"]

    del_res = await client.delete(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    get_res = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}",
        headers=headers,
    )
    assert get_res.status_code == 404


# ─── Requirement Items ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_requirement_items(client: AsyncClient):
    """Create items under a document, then list them."""
    token, user_id = await _register_login(client, "rq8@example.com", "rquser8")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    headers = {"Authorization": f"Bearer {token}"}
    doc_res = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"doc_type": "EIR", "title": "EIR"},
        headers=headers,
    )
    doc_id = doc_res.json()["id"]

    item1 = await client.post(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}/items",
        json={
            "item_no": "EIR-001",
            "what": "Provide IFC models for all structural elements",
        },
        headers=headers,
    )
    assert item1.status_code == 201
    assert item1.json()["item_no"] == "EIR-001"

    item2 = await client.post(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}/items",
        json={
            "item_no": "EIR-002",
            "what": "Naming must comply with ISO 19650-2",
            "when_required": "At each milestone",
            "for_whom": "Lead Appointed Party",
        },
        headers=headers,
    )
    assert item2.status_code == 201

    list_res = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{doc_id}/items",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2


@pytest.mark.asyncio
async def test_get_items_unknown_doc_returns_404(client: AsyncClient):
    """Listing items for unknown doc_id returns 404."""
    token, user_id = await _register_login(client, "rq9@example.com", "rquser9")
    org_id, project_id = await _setup_org_project()
    await _add_membership(user_id, org_id)

    res = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{uuid.uuid4()}/items",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
