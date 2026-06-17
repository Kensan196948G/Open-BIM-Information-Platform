"""Upload API tests.

Unit tests: always run (no external dependencies required)
Moto tests: run when moto[s3] is installed (dev dependency)
"""

import hashlib
import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import UserOrganization

# ─── Pure unit tests (no I/O required) ────────────────────────────────────────


def test_allowed_content_types_includes_bim_formats():
    from app.api.v1.uploads import ALLOWED_CONTENT_TYPES

    assert "model/ifc" in ALLOWED_CONTENT_TYPES
    assert "application/ifc" in ALLOWED_CONTENT_TYPES
    assert "application/pdf" in ALLOWED_CONTENT_TYPES


def test_allowed_content_types_rejects_renderable():
    """Renderable/executable types must be blocked (Stored XSS prevention)."""
    from app.api.v1.uploads import ALLOWED_CONTENT_TYPES

    for blocked in (
        "text/html",
        "application/javascript",
        "image/svg+xml",
        "text/javascript",
    ):
        assert blocked not in ALLOWED_CONTENT_TYPES, f"{blocked} must not be allowed"


def test_allowed_extensions_includes_bim_formats():
    from app.api.v1.uploads import ALLOWED_EXTENSIONS

    for ext in ("ifc", "bcf", "rvt", "pdf", "xlsx"):
        assert ext in ALLOWED_EXTENSIONS


def test_sanitize_extension_clean():
    from app.api.v1.uploads import _sanitize_extension

    assert _sanitize_extension("drawing.pdf") == "pdf"
    assert _sanitize_extension("model.ifc") == "ifc"
    assert _sanitize_extension("data.xlsx") == "xlsx"


def test_sanitize_extension_blocks_dangerous():
    from app.api.v1.uploads import _sanitize_extension

    assert _sanitize_extension("../../../etc/passwd") == "bin"
    assert _sanitize_extension("file.exe") == "bin"
    assert _sanitize_extension("malicious.php") == "bin"
    assert _sanitize_extension("attack.<script>") == "bin"


def test_storage_safe_ext():
    from app.services.storage import _safe_ext

    assert _safe_ext("model.ifc") == "ifc"
    assert _safe_ext("../../etc/passwd") == "bin"
    assert _safe_ext("noextension") == "bin"


def test_sha256_deterministic():
    """Same content always produces the same checksum."""
    data = b"BIM file content for integrity test"
    assert hashlib.sha256(data).hexdigest() == hashlib.sha256(data).hexdigest()
    assert len(hashlib.sha256(data).hexdigest()) == 64


# ─── Helpers for integration tests ────────────────────────────────────────────


async def _setup_org_project() -> tuple[str, str]:
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(Organization(id=org_id, name="Upload Org", slug=f"ul-{org_id[:8]}"))
        await session.commit()
        session.add(
            Project(
                id=proj_id, organization_id=org_id, name="Upload Project", code="UPL"
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
            "full_name": "UL User",
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


async def _create_container(client: AsyncClient, token: str, project_id: str) -> str:
    res = await client.post(
        f"/api/v1/projects/{project_id}/containers",
        json={"identifier": "UPL-ORG-XX-01-DR-A-0001", "title": "Upload Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ─── Moto-mocked S3 integration tests ─────────────────────────────────────────

try:
    import moto as _moto  # noqa: F401

    _HAS_MOTO = True
except ImportError:
    _HAS_MOTO = False

needs_moto = pytest.mark.skipif(not _HAS_MOTO, reason="moto[s3] not installed")


@pytest.fixture()
def mock_s3(monkeypatch):
    """Moto-mocked S3 environment. Skips automatically if moto is unavailable.

    Patches get_s3_client() to return a mock client without custom endpoint,
    so moto can intercept all boto3 calls (moto doesn't intercept custom endpoints).
    """
    if not _HAS_MOTO:
        pytest.skip("moto[s3] not installed")

    import boto3
    import moto

    from app import services

    with moto.mock_aws():
        # Create a client WITHOUT custom endpoint_url so moto can intercept it
        mock_client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        mock_client.create_bucket(Bucket="bim-containers")

        # Patch get_s3_client to return our moto-compatible client
        monkeypatch.setattr(services.storage, "get_s3_client", lambda: mock_client)
        monkeypatch.setattr(services.storage, "_s3_client", None)

        yield

        monkeypatch.setattr(services.storage, "_s3_client", None)


# ─── Auth guards (no moto needed — rejected before S3) ────────────────────────


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/fake-cid/upload",
        files={"file": ("x.pdf", b"data", "application/pdf")},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_download_url_requires_auth(client: AsyncClient):
    _, proj_id = await _setup_org_project()
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers/fake-cid/files/{uuid.uuid4()}/download-url",
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_download_url_not_found(client: AsyncClient):
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul_dl@ex.com", "ul_dl")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)
    nonexistent_file_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/projects/{proj_id}/containers/{cid}/files/{nonexistent_file_id}/download-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@needs_moto
@pytest.mark.asyncio
async def test_upload_rejects_html_mime(client: AsyncClient, mock_s3):
    """HTML must be rejected (Stored XSS prevention)."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul1@ex.com", "ul1")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("attack.html", b"<script>alert(1)</script>", "text/html")},
    )
    assert res.status_code == 415
    assert "not permitted" in res.json()["detail"]


@needs_moto
@pytest.mark.asyncio
async def test_upload_rejects_javascript_mime(client: AsyncClient, mock_s3):
    """JavaScript must be rejected."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul2@ex.com", "ul2")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("evil.js", b"pwned", "application/javascript")},
    )
    assert res.status_code == 415


@needs_moto
@pytest.mark.asyncio
async def test_upload_pdf_returns_sha256(client: AsyncClient, mock_s3):
    """Successful upload returns correct SHA-256 checksum and metadata."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul3@ex.com", "ul3")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    pdf_data = b"%PDF-1.4 test content for BIM platform"
    expected_sha = hashlib.sha256(pdf_data).hexdigest()

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("drawing.pdf", pdf_data, "application/pdf")},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["checksum_sha256"] == expected_sha
    assert data["file_size_bytes"] == len(pdf_data)
    assert data["original_filename"] == "drawing.pdf"
    assert data["container_id"] == cid


@needs_moto
@pytest.mark.asyncio
async def test_upload_ifc_accepted(client: AsyncClient, mock_s3):
    """IFC files (primary BIM format) must be accepted."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul4@ex.com", "ul4")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    ifc_data = b"ISO-10303-21; HEADER; END-HEADER; DATA; END-DATA; END-ISO-10303-21;"
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("model.ifc", ifc_data, "model/ifc")},
    )
    assert res.status_code == 201, res.text


@needs_moto
@pytest.mark.asyncio
async def test_upload_to_non_wip_container_rejected(client: AsyncClient, mock_s3):
    """Uploading to a non-WIP container returns 409 Conflict."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul5@ex.com", "ul5")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    # Transition to Shared (no longer WIP)
    await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/transition",
        json={"action": "submit"},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("drawing.pdf", b"data", "application/pdf")},
    )
    assert res.status_code == 409
    assert "WIP" in res.json()["detail"]


@needs_moto
@pytest.mark.asyncio
async def test_upload_rejects_non_member(client: AsyncClient, mock_s3):
    """Users not in the project org must receive 404 (IDOR protection)."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul6@ex.com", "ul6")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    outsider_token, _ = await _register_and_login(
        client, "outsider@ex.com", "outsider6"
    )
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {outsider_token}"},
        files={"file": ("drawing.pdf", b"data", "application/pdf")},
    )
    assert res.status_code == 404


@needs_moto
@pytest.mark.asyncio
async def test_upload_then_get_download_url(client: AsyncClient, mock_s3):
    """After upload, a presigned download URL can be retrieved."""
    org_id, proj_id = await _setup_org_project()
    token, user_id = await _register_and_login(client, "ul7@ex.com", "ul7")
    await _add_membership(user_id, org_id)
    cid = await _create_container(client, token, proj_id)

    upload_res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{cid}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("spec.pdf", b"BIM specification content", "application/pdf")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    dl_res = await client.get(
        f"/api/v1/projects/{proj_id}/containers/{cid}/files/{file_id}/download-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dl_res.status_code == 200
    data = dl_res.json()
    assert "download_url" in data
    assert data["expires_in_seconds"] == 3600
