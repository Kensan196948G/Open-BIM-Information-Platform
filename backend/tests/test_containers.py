"""Tests for /projects/{project_id}/containers endpoints."""

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
        org = Organization(
            id=org_id, name="Container Test Org", slug=f"corg-{org_id[:8]}"
        )
        session.add(org)
        await session.commit()
        project = Project(
            id=proj_id,
            organization_id=org_id,
            name="Container Test Project",
            code="CT-001",
        )
        session.add(project)
        await session.commit()
    return org_id, proj_id


async def _register_and_login(
    client: AsyncClient,
    email: str = "ct@example.com",
    username: str = "ctuser",
) -> tuple[str, str]:
    """Register user, login, return (token, user_id)."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": "Container Test User",
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
        membership = UserOrganization(
            user_id=user_id,
            organization_id=org_id,
            role_in_org="member",
        )
        session.add(membership)
        await session.commit()


async def _setup(client: AsyncClient, suffix: str = "0") -> tuple[str, str, str]:
    """Full setup: org + project + user + membership. Returns (token, proj_id, user_id)."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(
        client, f"ct{suffix}@example.com", f"ctuser{suffix}"
    )
    await _add_membership(user_id, org_id)
    return token, proj_id, user_id


async def _create_container(
    client: AsyncClient,
    token: str,
    proj_id: str,
    identifier: str = "PROJ-ORG-ZZ-GF-DR-AR-0001",
    title: str = "Test Container",
) -> dict:
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": identifier, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


# ─── List containers ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_containers_empty(client: AsyncClient):
    """Empty project returns empty list with total=0."""
    token, proj_id, _ = await _setup(client, "1")
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_containers_returns_created_item(client: AsyncClient):
    """After creating a container, list returns it."""
    token, proj_id, _ = await _setup(client, "2")
    await _create_container(client, token, proj_id)
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_containers_state_filter(client: AsyncClient):
    """State filter returns only containers matching that state."""
    token, proj_id, _ = await _setup(client, "3")
    await _create_container(
        client, token, proj_id, identifier="PROJ-ORG-ZZ-GF-DR-AR-0001"
    )
    # Filter for shared — should return 0 (container is still wip)
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers",
        params={"state": "Shared"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ─── Create container ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_container_compliant_naming(client: AsyncClient):
    """ISO 19650-compliant identifier → naming_valid=True."""
    token, proj_id, _ = await _setup(client, "4")
    res = await _create_container(
        client, token, proj_id, identifier="PROJ-ORG-ZZ-GF-DR-AR-0001"
    )
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is True
    assert data["naming_issues"] is None
    assert data["current_state"] == "WIP"
    assert data["identifier"] == "PROJ-ORG-ZZ-GF-DR-AR-0001"


@pytest.mark.asyncio
async def test_create_container_noncompliant_naming(client: AsyncClient):
    """Non-compliant identifier still creates container (naming is advisory) with naming_valid=False."""
    token, proj_id, _ = await _setup(client, "5")
    res = await _create_container(client, token, proj_id, identifier="BAD")
    assert res.status_code == 201
    data = res.json()
    assert data["naming_valid"] is False
    assert data["naming_issues"] is not None


@pytest.mark.asyncio
async def test_create_container_requires_auth(client: AsyncClient):
    """Creating a container without auth returns 401."""
    _, proj_id, _ = await _setup(client, "6")
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001", "title": "T"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_container_non_member_returns_404(client: AsyncClient):
    """Non-member cannot create containers — project appears as 404."""
    _, proj_id = await _setup_org_project()
    token2, _ = await _register_and_login(client, "ct7@example.com", "ctuser7")
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "PROJ-ORG-ZZ-GF-DR-AR-0001", "title": "T"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 404


# ─── Get container ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_container(client: AsyncClient):
    """GET single container returns correct data."""
    token, proj_id, _ = await _setup(client, "8")
    create_res = await _create_container(client, token, proj_id)
    container_id = create_res.json()["id"]

    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers/{container_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == container_id
    assert data["project_id"] == proj_id


@pytest.mark.asyncio
async def test_get_container_not_found(client: AsyncClient):
    """Unknown container ID returns 404."""
    token, proj_id, _ = await _setup(client, "9")
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


# ─── State transitions ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transition_wip_to_shared(client: AsyncClient):
    """WIP container + action=submit → state becomes shared."""
    token, proj_id, _ = await _setup(client, "10")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "Shared"


@pytest.mark.asyncio
async def test_transition_shared_to_published(client: AsyncClient):
    """shared container + action=approve → state becomes published."""
    token, proj_id, _ = await _setup(client, "11")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]

    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "Published"


@pytest.mark.asyncio
async def test_transition_shared_to_wip_via_return(client: AsyncClient):
    """shared container + action=return → state reverts to wip."""
    token, proj_id, _ = await _setup(client, "12")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "return"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "WIP"


@pytest.mark.asyncio
async def test_transition_invalid_action_returns_409(client: AsyncClient):
    """Invalid action for current state returns 409."""
    token, proj_id, _ = await _setup(client, "13")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    # WIP cannot be approved directly
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_transition_target_state_mismatch_returns_409(client: AsyncClient):
    """Correct action + wrong expected target_state → 409 conflict."""
    token, proj_id, _ = await _setup(client, "14")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    # submit yields 'shared', but client claims 'published'
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit", "target_state": "Published"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_transition_with_correct_target_state(client: AsyncClient):
    """Correct action + matching target_state succeeds."""
    token, proj_id, _ = await _setup(client, "15")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit", "target_state": "Shared"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "Shared"


@pytest.mark.asyncio
async def test_transition_with_comment(client: AsyncClient):
    """Transition with comment succeeds and state changes."""
    token, proj_id, _ = await _setup(client, "16")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit", "comment": "Ready for review"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "Shared"


# ─── Update container ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_container_wip(client: AsyncClient):
    """PATCH on WIP container updates title."""
    token, proj_id, _ = await _setup(client, "17")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]

    res = await client.patch(
        f"/api/v1/projects/{proj_id}/containers/{container_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_container_non_wip_returns_409(client: AsyncClient):
    """PATCH on shared (non-WIP) container returns 409."""
    token, proj_id, _ = await _setup(client, "18")
    container_id = (await _create_container(client, token, proj_id)).json()["id"]
    # Move to shared
    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.patch(
        f"/api/v1/projects/{proj_id}/containers/{container_id}",
        json={"title": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_update_container_not_found(client: AsyncClient):
    """PATCH on unknown container returns 404."""
    token, proj_id, _ = await _setup(client, "19")
    res = await client.patch(
        f"/api/v1/projects/{proj_id}/containers/{uuid.uuid4()}",
        json={"title": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


# ─── Access control ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_containers_non_member_returns_404(client: AsyncClient):
    """Non-member cannot list containers — project returns 404."""
    _, proj_id = await _setup_org_project()
    token, _ = await _register_and_login(client, "ct20@example.com", "ctuser20")
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_containers_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    _, proj_id = await _setup_org_project()
    res = await client.get(f"/api/v1/projects/{proj_id}/containers")
    assert res.status_code == 401
