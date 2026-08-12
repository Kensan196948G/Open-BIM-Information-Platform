"""OIDC PoC tests using an in-process fake identity provider."""

import base64
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form
from httpx import ASGITransport, AsyncClient
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.services import oidc as oidc_service

ISSUER = "https://issuer.example.com"
CLIENT_ID = "bim-client"
CLIENT_SECRET = "client-secret"
REDIRECT_URI = "https://bim.example.com/api/v1/auth/oidc/callback"


def _b64_int(value: int) -> str:
    return (
        base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big"))
        .rstrip(b"=")
        .decode()
    )


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


@pytest.fixture
def fake_oidc_provider(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private_key.public_key().public_numbers()
    jwks_key = {
        "kty": "RSA",
        "kid": "test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _b64_int(public.n),
        "e": _b64_int(public.e),
    }
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    def _sign(claims: dict) -> str:
        return jose_jwt.encode(
            claims, pem, algorithm="RS256", headers={"kid": "test-key"}
        )

    app = FastAPI()

    @app.get("/.well-known/openid-configuration")
    async def discovery():
        return {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "userinfo_endpoint": f"{ISSUER}/userinfo",
            "jwks_uri": f"{ISSUER}/jwks",
        }

    @app.get("/jwks")
    async def jwks():
        return {"keys": [jwks_key]}

    @app.post("/token")
    async def token(
        code: str = Form(...),
        code_verifier: str = Form(...),
        grant_type: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        redirect_uri: str = Form(...),
    ):
        # The test encodes the nonce inside the authorization code.
        nonce = _b64url_decode(code).decode()
        now = datetime.now(UTC)
        id_token = _sign(
            {
                "iss": ISSUER,
                "sub": "sub-oidc-123",
                "aud": CLIENT_ID,
                "email": "oidc@example.com",
                "name": "OIDC User",
                "nonce": nonce,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=5)).timestamp()),
            }
        )
        return {
            "access_token": "fake-access-token",
            "id_token": id_token,
            "token_type": "Bearer",
            "expires_in": 300,
        }

    @app.get("/userinfo")
    async def userinfo():
        return {"sub": "sub-oidc-123", "email": "oidc@example.com"}

    def _client(**kwargs) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url=ISSUER, **kwargs)

    monkeypatch.setattr(oidc_service.httpx, "AsyncClient", _client)
    monkeypatch.setattr(settings, "OIDC_ENABLED", True)
    monkeypatch.setattr(settings, "OIDC_ISSUER", ISSUER)
    monkeypatch.setattr(settings, "OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(settings, "OIDC_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setattr(settings, "OIDC_REDIRECT_URI", REDIRECT_URI)
    oidc_service._discovery_cache.clear()
    yield
    oidc_service._discovery_cache.clear()


async def _get_authorize_state(client: AsyncClient) -> tuple[str, dict]:
    res = await client.get("/api/v1/auth/oidc/authorize")
    assert res.status_code == 307
    location = res.headers["location"]
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    import urllib.parse

    query = urllib.parse.urlparse(location).query
    params = urllib.parse.parse_qs(query)
    state = params["state"][0]
    payload = oidc_service.decode_oidc_state(state)
    return state, payload


@pytest.mark.asyncio
async def test_oidc_disabled_returns_404(client: AsyncClient):
    res = await client.get("/api/v1/auth/oidc/authorize")
    assert res.status_code == 404
    config = await client.get("/api/v1/auth/oidc/config")
    assert config.json()["enabled"] is False


@pytest.mark.asyncio
async def test_oidc_full_login_flow(client: AsyncClient, fake_oidc_provider):
    state, payload = await _get_authorize_state(client)
    code = base64.urlsafe_b64encode(payload["nonce"].encode()).rstrip(b"=").decode()

    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": code, "state": state},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"

    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == "oidc@example.com"))
        ).scalar_one()
        assert user.oidc_sub == "sub-oidc-123"
        assert user.is_active is True


@pytest.mark.asyncio
async def test_oidc_domain_allowlist_blocks_other_domains(
    client: AsyncClient, fake_oidc_provider, monkeypatch
):
    """OIDC login must be rejected when the email domain is not allowed."""
    monkeypatch.setattr(settings, "OIDC_ALLOWED_DOMAINS", "allowed.example.com")
    state, payload = await _get_authorize_state(client)
    code = base64.urlsafe_b64encode(payload["nonce"].encode()).rstrip(b"=").decode()

    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": code, "state": state},
    )
    assert res.status_code == 403
    assert "domain is not permitted" in res.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_domain_allowlist_allows_matching_domain(
    client: AsyncClient, fake_oidc_provider, monkeypatch
):
    """OIDC login succeeds when the email domain is in the allowlist."""
    monkeypatch.setattr(settings, "OIDC_ALLOWED_DOMAINS", "example.com")
    state, payload = await _get_authorize_state(client)
    code = base64.urlsafe_b64encode(payload["nonce"].encode()).rstrip(b"=").decode()

    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": code, "state": state},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_oidc_jit_inactive_blocks_login(
    client: AsyncClient, fake_oidc_provider, monkeypatch
):
    monkeypatch.setattr(settings, "OIDC_JIT_ACTIVE", False)
    state, payload = await _get_authorize_state(client)
    code = base64.urlsafe_b64encode(payload["nonce"].encode()).rstrip(b"=").decode()

    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": code, "state": state},
    )
    assert res.status_code == 403
    assert "not activated" in res.json()["detail"]

    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == "oidc@example.com"))
        ).scalar_one()
        assert user.is_active is False


@pytest.mark.asyncio
async def test_oidc_invalid_state_returns_400(client: AsyncClient, fake_oidc_provider):
    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": "x", "state": "tampered-state"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_oidc_nonce_mismatch_returns_401(client: AsyncClient, fake_oidc_provider):
    state, _ = await _get_authorize_state(client)
    wrong_nonce = base64.urlsafe_b64encode(b"other-nonce").rstrip(b"=").decode()
    res = await client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": wrong_nonce, "state": state},
    )
    assert res.status_code == 401
    assert "Nonce mismatch" in res.json()["detail"]


@pytest.mark.no_db
def test_verify_id_token_rejects_wrong_key():
    from jose import jwt as jose_jwt

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = other_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    token = jose_jwt.encode(
        {"iss": ISSUER, "sub": "x", "aud": CLIENT_ID},
        pem,
        algorithm="RS256",
    )
    with pytest.raises(JWTError):
        oidc_service.verify_id_token_with_keys(token, [])


@pytest.mark.no_db
def test_derive_username_short_and_long():
    assert oidc_service.derive_username("user@example.com") == "user"
    long_email = "very-long-local-part-" + "x" * 100 + "@example.com"
    username = oidc_service.derive_username(long_email)
    assert len(username) <= 100
    assert "-" in username
    assert username == oidc_service.derive_username(long_email)
