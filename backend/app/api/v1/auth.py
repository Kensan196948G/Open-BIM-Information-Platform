import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DB, CurrentUser
from app.core.ratelimit import rate_limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _login_rate_limit(request: Request) -> None:
    ip = _client_ip(request) or "unknown"
    if not await rate_limiter.allow(
        (ip, "login"),
        settings.LOGIN_RATE_LIMIT,
        settings.LOGIN_RATE_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )


async def _register_rate_limit(request: Request) -> None:
    ip = _client_ip(request) or "unknown"
    if not await rate_limiter.allow(
        (ip, "register"),
        settings.REGISTER_RATE_LIMIT,
        settings.REGISTER_RATE_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts from this address.",
        )


async def _revoke_token(db, token: str, token_type: str) -> None:
    """Revoke a JWT by its jti (best-effort; invalid tokens are ignored)."""
    try:
        payload = decode_token(token)
    except JWTError:
        return
    jti = payload.get("jti")
    if not jti:
        return
    existing = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    if existing.scalar_one_or_none() is not None:
        return
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
    db.add(
        RevokedToken(
            id=str(uuid.uuid4()),
            jti=jti,
            token_type=token_type,
            expires_at=expires_at,
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DB,
    _: Annotated[None, Depends(_login_rate_limit)] = None,
) -> TokenResponse:
    ip = _client_ip(request)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        record_audit(
            db,
            event_type="user.login_failed",
            operation="login",
            target_type="user",
            target_id=None,
            actor_ip=ip,
            result="failure",
            reason="unknown user or missing password",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not verify_password(form_data.password, user.hashed_password):
        record_audit(
            db,
            event_type="user.login_failed",
            operation="login",
            target_type="user",
            target_id=user.id,
            actor_id=user.id,
            actor_ip=ip,
            result="failure",
            reason="invalid password",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        record_audit(
            db,
            event_type="user.login_rejected",
            operation="login",
            target_type="user",
            target_id=user.id,
            actor_id=user.id,
            actor_ip=ip,
            result="failure",
            reason="account disabled",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )

    record_audit(
        db,
        event_type="user.login",
        operation="login",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
        actor_ip=ip,
        result="success",
    )
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: Request,
    body: UserCreate,
    db: DB,
    _: Annotated[None, Depends(_register_rate_limit)] = None,
) -> UserResponse:
    if not settings.ALLOW_SELF_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled. Contact your administrator.",
        )
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        record_audit(
            db,
            event_type="user.registration_rejected",
            operation="register",
            target_type="user",
            actor_ip=_client_ip(request),
            result="failure",
            reason="duplicate email",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=body.email,
        username=body.username,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    record_audit(
        db,
        event_type="user.registered",
        operation="register",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: DB,
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    jti = payload.get("jti")
    if jti:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing a subject",
        )
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Rotation: revoke the presented refresh token and issue a new pair.
    if jti:
        await _revoke_token(db, body.refresh_token, "refresh")
    record_audit(
        db,
        event_type="token.refreshed",
        operation="refresh",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DB,
    body: LogoutRequest | None = None,
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    actor_id = payload.get("sub")
    await _revoke_token(db, credentials.credentials, "access")
    if body and body.refresh_token:
        await _revoke_token(db, body.refresh_token, "refresh")
    record_audit(
        db,
        event_type="user.logout",
        operation="logout",
        target_type="user",
        target_id=actor_id,
        actor_id=actor_id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
