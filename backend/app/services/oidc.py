"""Generic OIDC (Authorization Code + PKCE) client for Entra ID / HENNGE."""

import base64
import hashlib
import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta

import httpx
from jose import JWTError, jwk, jwt

from app.core.config import settings

_discovery_cache: dict[str, dict] = {}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_pkce_pair() -> tuple[str, str]:
    verifier = _b64url_encode(secrets.token_bytes(48))
    challenge = _b64url_encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def create_oidc_state(nonce: str, code_verifier: str) -> str:
    """Signed state token: the callback needs the verifier/nonce to proceed."""
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "nonce": nonce,
            "code_verifier": code_verifier,
            "exp": now + timedelta(minutes=10),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_oidc_state(state: str) -> dict:
    return jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


async def get_discovery() -> dict:
    issuer = settings.OIDC_ISSUER.rstrip("/")
    if issuer in _discovery_cache:
        return _discovery_cache[issuer]
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        discovery = response.json()
    _discovery_cache[issuer] = discovery
    return discovery


async def get_jwks() -> list[dict]:
    discovery = await get_discovery()
    jwks_uri = settings.OIDC_JWKS_URI or discovery.get("jwks_uri")
    if not jwks_uri:
        raise OSError("OIDC discovery did not provide jwks_uri")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(jwks_uri)
        response.raise_for_status()
    return response.json().get("keys", [])


def verify_id_token_with_keys(id_token: str, keys: list[dict]) -> dict:
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    candidates = [k for k in keys if not kid or k.get("kid") == kid] or keys
    last_error: Exception | None = None
    for key_dict in candidates:
        try:
            key = jwk.construct(key_dict)
            pem = key.to_pem().decode() if hasattr(key, "to_pem") else key_dict
            claims = jwt.decode(
                id_token,
                pem,
                algorithms=["RS256", "RS384", "RS512"],
                audience=settings.OIDC_CLIENT_ID,
                issuer=settings.OIDC_ISSUER.rstrip("/"),
                options={"verify_at_hash": False},
            )
            return claims
        except Exception as exc:  # noqa: BLE001 - try next key
            last_error = exc
    raise JWTError(f"ID token verification failed: {last_error}")


async def create_authorization_url() -> tuple[str, str]:
    """Returns (authorization_url, state_token)."""
    discovery = await get_discovery()
    nonce = _b64url_encode(secrets.token_bytes(24))
    verifier, challenge = create_pkce_pair()
    state = create_oidc_state(nonce, verifier)
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": settings.OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = discovery["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)
    return url, state


async def exchange_code(code: str, code_verifier: str) -> dict:
    discovery = await get_discovery()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "client_secret": settings.OIDC_CLIENT_SECRET,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            discovery["token_endpoint"],
            data=data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_userinfo(access_token: str) -> dict:
    discovery = await get_discovery()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            discovery["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
