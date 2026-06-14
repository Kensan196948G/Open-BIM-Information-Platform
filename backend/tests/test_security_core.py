"""Unit tests for app/core/security.py and app/core/deps.py."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

pytestmark = pytest.mark.no_db


# ─── security.py ─────────────────────────────────────────────────────────────


def test_hash_and_verify_password():
    """hash_password + verify_password round-trip succeeds."""
    from app.core.security import hash_password, verify_password

    plain = "SecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_verify_password_wrong_password():
    """verify_password returns False for wrong password."""
    from app.core.security import hash_password, verify_password

    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_create_access_token_default_expiry():
    """create_access_token encodes subject and type=access."""
    from app.core.config import settings
    from app.core.security import create_access_token

    token = create_access_token("user-123")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    """create_access_token respects custom expires_delta."""
    from app.core.config import settings
    from app.core.security import create_access_token

    delta = timedelta(minutes=5)
    before = datetime.now(UTC)
    token = create_access_token("user-456", expires_delta=delta)
    after = datetime.now(UTC)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

    # JWT exp is truncated to whole seconds; allow 2s tolerance
    assert before + delta - timedelta(seconds=1) <= exp <= after + delta + timedelta(seconds=2)


def test_create_refresh_token():
    """create_refresh_token encodes subject and type=refresh."""
    from app.core.config import settings
    from app.core.security import create_refresh_token

    token = create_refresh_token("user-789")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "user-789"
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_create_refresh_token_expiry_in_days():
    """create_refresh_token expires in configured REFRESH_TOKEN_EXPIRE_DAYS."""
    from app.core.config import settings
    from app.core.security import create_refresh_token

    token = create_refresh_token("user-abc")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expected_min = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS - 1)
    expected_max = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS + 1)

    assert expected_min < exp < expected_max


def test_decode_token_valid():
    """decode_token returns payload dict for a valid token."""
    from app.core.security import create_access_token, decode_token

    token = create_access_token("user-decode")
    payload = decode_token(token)

    assert payload["sub"] == "user-decode"


def test_decode_token_invalid_raises():
    """decode_token raises JWTError for a tampered token."""
    from jose import JWTError

    from app.core.security import decode_token

    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_decode_token_expired_raises():
    """decode_token raises JWTError for an expired token."""
    from jose import JWTError, jwt

    from app.core.config import settings
    from app.core.security import decode_token

    # Create a token that expired 1 second ago
    expired_payload = {
        "sub": "user-expired",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
        "type": "access",
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(JWTError):
        decode_token(expired_token)


# ─── deps.py ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_success():
    """get_current_user returns the user when token and DB are valid."""
    from app.core.deps import get_current_user
    from app.core.security import create_access_token

    token = create_access_token("user-id-001")

    mock_user = MagicMock()
    mock_user.id = "user-id-001"
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_credentials = MagicMock()
    mock_credentials.credentials = token

    user = await get_current_user(credentials=mock_credentials, db=mock_db)
    assert user is mock_user


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_raises():
    """get_current_user raises 401 for an invalid token (JWTError branch)."""
    from app.core.deps import get_current_user

    mock_credentials = MagicMock()
    mock_credentials.credentials = "invalid.token.here"

    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=mock_credentials, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_raises():
    """get_current_user raises 401 when token has no 'sub' claim."""
    from jose import jwt

    from app.core.config import settings
    from app.core.deps import get_current_user

    # Token with no 'sub' field
    token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(hours=1), "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    mock_credentials = MagicMock()
    mock_credentials.credentials = token

    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=mock_credentials, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found_raises():
    """get_current_user raises 401 when user does not exist in DB."""
    from app.core.deps import get_current_user
    from app.core.security import create_access_token

    token = create_access_token("nonexistent-user")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_credentials = MagicMock()
    mock_credentials.credentials = token

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=mock_credentials, db=mock_db)

    assert exc_info.value.status_code == 401
