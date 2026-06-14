"""Integration tests for /api/v1/naming/validate endpoint."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.naming_rule import ProjectNamingRule
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization

# ─── Helpers ──────────────────────────────────────────────────────────────────

_VALID_ISO = "PROJ-ORG-ZZ-GF-DR-AR-0001"  # valid ISO 19650 identifier


async def _setup_org_project() -> tuple[str, str]:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        org = Organization(id=org_id, name="NV Org", slug=f"nv-org-{org_id[:8]}")
        session.add(org)
        await session.commit()
        project = Project(
            id=proj_id,
            organization_id=org_id,
            name="NV Project",
            code="NVP",
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
            "full_name": "NV User",
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


async def _set_custom_rule(proj_id: str, separator: str, segments: list) -> None:
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        rule = ProjectNamingRule(
            project_id=proj_id,
            separator=separator,
            segments=segments,
        )
        session.add(rule)
        await session.commit()


# ─── Auth guard ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_unauthenticated_returns_401(client: AsyncClient):
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO},
    )
    assert res.status_code == 401


# ─── Default rule (no project_id) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_compliant_identifier_default_rule(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv1@example.com", "nv1")
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["identifier"] == _VALID_ISO
    assert data["is_compliant"] is True
    assert data["level"] in ("ok", "warning", "error")
    assert isinstance(data["issues"], list)


@pytest.mark.asyncio
async def test_validate_noncompliant_identifier_default_rule(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv2@example.com", "nv2")
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_compliant"] is False
    assert len(data["issues"]) > 0
    assert data["issues_text"] != ""


@pytest.mark.asyncio
async def test_validate_empty_identifier_is_noncompliant(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv3@example.com", "nv3")
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is False


# ─── Project-specific rule (member) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_uses_project_rule_when_member(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nv4@example.com", "nv4")
    await _add_membership(user_id, org_id)

    # Custom 2-segment rule: PROJ_NUM
    await _set_custom_rule(
        proj_id,
        separator="_",
        segments=[
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    )

    # Identifier that matches custom rule
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "ABC_001", "project_id": proj_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is True


@pytest.mark.asyncio
async def test_validate_custom_rule_rejects_iso_format(client: AsyncClient):
    """Custom 2-segment rule rejects the standard ISO 7-segment identifier."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "nv5@example.com", "nv5")
    await _add_membership(user_id, org_id)

    await _set_custom_rule(
        proj_id,
        separator="_",
        segments=[
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    )

    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO, "project_id": proj_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is False


# ─── Non-member fallback ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_non_member_falls_back_to_default(client: AsyncClient):
    """Non-member gets default ISO rule instead of project-specific rule."""
    org_id, proj_id = await _setup_org_project()
    # Register user but do NOT add membership
    token, _ = await _register_and_login(client, "nv6@example.com", "nv6")

    await _set_custom_rule(
        proj_id,
        separator="_",
        segments=[
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    )

    # Standard ISO identifier should be compliant because default rule is used
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO, "project_id": proj_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    # Default ISO rule → _VALID_ISO is compliant
    assert res.json()["is_compliant"] is True


# ─── Unknown project_id ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_unknown_project_falls_back_to_default(client: AsyncClient):
    """Non-existent project_id falls back to default ISO rule (no 404)."""
    token, _ = await _register_and_login(client, "nv7@example.com", "nv7")
    nonexistent = str(uuid.uuid4())
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO, "project_id": nonexistent},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_compliant"] is True


# ─── Response schema ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_response_has_required_fields(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv8@example.com", "nv8")
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "identifier" in data
    assert "level" in data
    assert "is_compliant" in data
    assert "issues" in data
    assert "issues_text" in data


@pytest.mark.asyncio
async def test_validate_issue_objects_have_required_fields(client: AsyncClient):
    token, _ = await _register_and_login(client, "nv9@example.com", "nv9")
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": "bad-identifier"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    issues = res.json()["issues"]
    for issue in issues:
        assert "segment_key" in issue
        assert "segment_label" in issue
        assert "level" in issue
        assert "message" in issue


# ─── Platform admin uses project rule without membership ───────────────────────


@pytest.mark.asyncio
async def test_platform_admin_uses_project_rule_without_membership(client: AsyncClient):
    """Platform admin bypasses org membership check and gets project-specific rule."""
    from app.models.user import User
    from tests.conftest import TestSessionLocal

    org_id, proj_id = await _setup_org_project()

    await _set_custom_rule(
        proj_id,
        separator="_",
        segments=[
            {
                "key": "proj",
                "label": "Project",
                "required": True,
                "pattern": "^[A-Z]+$",
            },
            {"key": "num", "label": "Number", "required": True, "pattern": "^\\d+$"},
        ],
    )

    # Register admin user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nvadmin@example.com",
            "username": "nvadmin",
            "full_name": "NV Admin",
            "password": "pass1234",
        },
    )
    admin_id = reg.json()["id"]

    # Promote to platform admin
    async with TestSessionLocal() as session:
        result = await session.get(User, admin_id)
        result.is_platform_admin = True
        await session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "nvadmin@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    admin_token = login_res.json()["access_token"]

    # Admin has no membership but should get custom rule → ISO format rejected
    res = await client.post(
        "/api/v1/naming/validate",
        json={"identifier": _VALID_ISO, "project_id": proj_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    # Custom 2-segment rule: ISO 7-segment format should be non-compliant
    assert res.json()["is_compliant"] is False
