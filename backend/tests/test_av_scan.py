"""ClamAV (clamd) client tests using a fake clamd TCP server."""

import asyncio
import struct

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.av_scan import ping_clamd, scan_bytes

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


async def _serve_clamd(reader, writer, virus: bool) -> None:
    try:
        while True:
            line = await reader.readline()
            if not line:
                return
            assert line == b"PING\n"
            writer.write(b"PONG\0")
            await writer.drain()

            marker = await reader.readexactly(10)
            assert marker == b"zINSTREAM\0"
            while True:
                size_b = await reader.readexactly(4)
                size = struct.unpack(">I", size_b)[0]
                if size == 0:
                    break
                remaining = size
                while remaining > 0:
                    chunk = await reader.read(min(remaining, 65536))
                    if not chunk:
                        return
                    remaining -= len(chunk)
            response = b"stream: Eicar-Test-Signature FOUND" if virus else b"stream: OK"
            writer.write(response + b"\0")
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
        return


@pytest.fixture
async def start_clamd():
    servers = []

    async def _start(virus: bool = False) -> int:
        server = await asyncio.start_server(
            lambda r, w: _serve_clamd(r, w, virus), "127.0.0.1", 0
        )
        servers.append(server)
        return server.sockets[0].getsockname()[1]

    yield _start

    for server in servers:
        server.close()


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_ping_clamd(start_clamd, monkeypatch):
    port = await start_clamd()
    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    await ping_clamd()


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_scan_clean_file(start_clamd, monkeypatch):
    port = await start_clamd(virus=False)
    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    result = await scan_bytes(b"%PDF-1.7 clean document")
    assert result.clean is True
    assert "OK" in result.reason


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_scan_detects_virus(start_clamd, monkeypatch):
    port = await start_clamd(virus=True)
    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    result = await scan_bytes(EICAR)
    assert result.clean is False
    assert "FOUND" in result.reason


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_scan_unavailable_raises(monkeypatch):
    # Start and immediately close a server to obtain a free-but-closed port.
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    with pytest.raises(OSError):
        await scan_bytes(b"data")


# ─── Upload integration ───────────────────────────────────────────────────────


async def _setup(client: AsyncClient) -> tuple[str, str, str]:
    import uuid

    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.user import UserOrganization
    from tests.conftest import TestSessionLocal

    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        session.add(Organization(id=org_id, name="AV Org", slug=f"av-{org_id[:8]}"))
        await session.commit()
        session.add(
            Project(
                id=proj_id,
                organization_id=org_id,
                name="AV Project",
                code="AVP",
            )
        )
        await session.commit()

    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "av@example.com",
            "username": "avuser",
            "full_name": "AV User",
            "password": "pass1234",
        },
    )
    user_id = reg.json()["id"]
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "av@example.com", "password": "pass1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    async with TestSessionLocal() as session:
        session.add(UserOrganization(user_id=user_id, organization_id=org_id))
        await session.commit()

    cont = await client.post(
        f"/api/v1/projects/{proj_id}/containers",
        json={"identifier": "AVP-ORG-XX-01-DR-A-0001", "title": "AV Container"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cont.status_code == 201, cont.text
    return token, proj_id, cont.json()["id"]


@pytest.mark.asyncio
async def test_upload_rejects_eicar_when_av_enabled(
    client: AsyncClient, start_clamd, monkeypatch
):
    port = await start_clamd(virus=True)
    monkeypatch.setattr(settings, "AV_ENABLED", True)
    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    token, proj_id, container_id = await _setup(client)
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("eicar.pdf", EICAR, "application/pdf")},
    )
    assert res.status_code == 422
    assert "malware scanner" in res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_clean_file_when_av_enabled(
    client: AsyncClient, start_clamd, monkeypatch, mock_s3
):
    port = await start_clamd(virus=False)
    monkeypatch.setattr(settings, "AV_ENABLED", True)
    monkeypatch.setattr(settings, "CLAMD_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "CLAMD_PORT", port)

    token, proj_id, container_id = await _setup(client)
    res = await client.post(
        f"/api/v1/projects/{proj_id}/containers/{container_id}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("clean.pdf", b"%PDF-1.7 clean", "application/pdf")},
    )
    assert res.status_code == 201, res.text
    assert res.json()["checksum_sha256"]
