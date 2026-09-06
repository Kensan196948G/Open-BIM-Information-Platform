"""External share request workflow tests (Issue #55)."""

import uuid
from datetime import UTC, datetime, timedelta

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
            Organization(id=org_id, name="Share Org", slug=f"share-{org_id[:8]}")
        )
        await session.commit()
        session.add(
            Project(
                id=proj_id, organization_id=org_id, name="Share Project", code="SHR"
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
            "full_name": "Share User",
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


async def _member_and_reviewer(client: AsyncClient, org_id: str) -> tuple[str, str]:
    member_token, member_id = await _register_and_login(
        client, "share_m@example.com", "sharem"
    )
    reviewer_token, reviewer_id = await _register_and_login(
        client, "share_r@example.com", "sharer"
    )
    await _add_membership(member_id, org_id, role="member")
    await _add_membership(reviewer_id, org_id, role="reviewer")
    return member_token, reviewer_token


async def _create_container(client: AsyncClient, token: str, project_id: str) -> str:
    res = await client.post(
        f"/api/v1/projects/{project_id}/containers",
        json={"identifier": "SHR-ORG-XX-01-DR-A-0001", "title": "Share Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _share_url(project_id: str, container_id: str, suffix: str = "") -> str:
    return f"/api/v1/projects/{project_id}/containers/{container_id}/share-requests{suffix}"


def _parse_dt(value: str) -> datetime:
    """Parse an ISO timestamp, assuming UTC if the SQLite round-trip dropped tzinfo."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


try:
    import moto as _moto  # noqa: F401

    _HAS_MOTO = True
except ImportError:
    _HAS_MOTO = False

needs_moto = pytest.mark.skipif(not _HAS_MOTO, reason="moto[s3] not installed")


# ─── Create ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_share_request_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.post(_share_url(proj_id, "fake-cid"), json={"reason": "x"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_member_can_create_share_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)

    res = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "external review needed"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "pending"
    assert data["reason"] == "external review needed"
    assert data["container_id"] == cid
    assert data["expires_at"] is None
    assert "token" not in data


@pytest.mark.asyncio
async def test_list_share_requests(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)

    await client.post(
        _share_url(proj_id, cid),
        json={"reason": "r1"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    res = await client.get(
        _share_url(proj_id, cid),
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["reason"] == "r1"


@pytest.mark.asyncio
async def test_create_share_request_non_member_returns_404(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)

    outsider_token, _ = await _register_and_login(
        client, "outsider_share@example.com", "outsider_share"
    )
    res = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "x"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert res.status_code == 404


# ─── Approve ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reviewer_can_approve_share_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)

    created = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "for client review"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    before = datetime.now(UTC)
    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={"expires_in_hours": 48},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "approved"
    assert data["token"] is not None and len(data["token"]) >= 32
    assert data["share_url_path"] == f"/api/v1/public/shared/{data['token']}"

    expires_at = _parse_dt(data["expires_at"])
    delta = expires_at - before
    assert timedelta(hours=47) < delta < timedelta(hours=49)


@pytest.mark.asyncio
async def test_approve_defaults_to_72_hours(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    before = datetime.now(UTC)
    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200
    expires_at = _parse_dt(res.json()["expires_at"])
    delta = expires_at - before
    assert timedelta(hours=71) < delta < timedelta(hours=73)


@pytest.mark.asyncio
async def test_member_cannot_approve_share_request(client: AsyncClient):
    """Separation of duties: a plain member must not approve (403)."""
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "r"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_approve_already_approved_returns_409(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    first = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert first.status_code == 200
    second = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert second.status_code == 409


# ─── Reject ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reviewer_can_reject_share_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "r"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/reject"),
        json={"reason": "not appropriate for external sharing"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_member_cannot_reject_share_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/reject"),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 403


# ─── Revoke ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_requester_can_revoke_own_pending_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/revoke"),
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_other_member_cannot_revoke_someone_elses_request(
    client: AsyncClient,
):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]

    other_token, other_id = await _register_and_login(
        client, "other_share@example.com", "othershare"
    )
    await _add_membership(other_id, org_id, role="member")

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/revoke"),
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_can_revoke_approved_request(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/revoke"),
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "revoked"


# ─── Public download endpoint ───────────────────────────────────────────────


@needs_moto
@pytest.mark.asyncio
async def test_public_download_succeeds_for_approved_token(
    client: AsyncClient, mock_s3
):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)

    file_bytes = b"BIM export content for external partner"
    upload_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {member_token}"},
        files={"file": ("export.pdf", file_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201, upload_res.text

    created = await client.post(
        _share_url(proj_id, cid),
        json={"reason": "external partner"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    approved = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={"expires_in_hours": 24},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    token = approved.json()["token"]

    res = await client.get(f"/api/v1/public/shared/{token}")
    assert res.status_code == 200, res.text
    assert res.content == file_bytes
    assert "attachment" in res.headers["content-disposition"]
    assert "export.pdf" in res.headers["content-disposition"]


@pytest.mark.asyncio
async def test_public_download_unknown_token_returns_404(client: AsyncClient):
    res = await client.get(
        f"/api/v1/public/shared/{'a' * 43}",
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_public_download_pending_request_returns_404(client: AsyncClient):
    """A share request that was never approved has no token — never leaks."""
    org_id, proj_id = await _setup_org_project()
    member_token, _ = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    # No token was ever issued, so any guessed token must 404.
    res = await client.get(f"/api/v1/public/shared/{'b' * 43}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_public_download_rejected_request_returns_404(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/reject"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    res = await client.get(f"/api/v1/public/shared/{'c' * 43}")
    assert res.status_code == 404


@needs_moto
@pytest.mark.asyncio
async def test_public_download_revoked_token_returns_404(client: AsyncClient, mock_s3):
    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {member_token}"},
        files={"file": ("f.pdf", b"content", "application/pdf")},
    )
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    approved = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    token = approved.json()["token"]

    revoke_res = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/revoke"),
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert revoke_res.status_code == 200

    res = await client.get(f"/api/v1/public/shared/{token}")
    assert res.status_code == 404


@needs_moto
@pytest.mark.asyncio
async def test_public_download_expired_token_returns_404(client: AsyncClient, mock_s3):
    """Manually back-date expires_at and confirm the endpoint 404s."""
    from sqlalchemy import select

    from app.models.share_request import ShareRequest
    from tests.conftest import TestSessionLocal

    org_id, proj_id = await _setup_org_project()
    member_token, reviewer_token = await _member_and_reviewer(client, org_id)
    cid = await _create_container(client, member_token, proj_id)
    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {member_token}"},
        files={"file": ("f.pdf", b"content", "application/pdf")},
    )
    created = await client.post(
        _share_url(proj_id, cid),
        json={},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    sr_id = created.json()["id"]
    approved = await client.post(
        _share_url(proj_id, cid, f"/{sr_id}/approve"),
        json={},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    token = approved.json()["token"]

    async with TestSessionLocal() as session:
        row = (
            await session.execute(select(ShareRequest).where(ShareRequest.id == sr_id))
        ).scalar_one()
        row.expires_at = datetime.now(UTC) - timedelta(hours=1)
        session.add(row)
        await session.commit()

    res = await client.get(f"/api/v1/public/shared/{token}")
    assert res.status_code == 404
