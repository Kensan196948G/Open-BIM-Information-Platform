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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str


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


def _auth_bypass_enabled() -> bool:
    """MVP 公開デモ用のログイン認証バイパスが有効かどうか。

    AUTH_BYPASS=True のときだけ有効。さらに ENVIRONMENT が "production" の
    場合は設定値によらず必ず無効にする（安全装置）。
    """
    if not settings.AUTH_BYPASS:
        return False
    return settings.ENVIRONMENT.strip().lower() != "production"


@router.post("/demo-login", response_model=TokenResponse, include_in_schema=False)
async def demo_login(request: Request, db: DB) -> TokenResponse:
    """MVP 公開デモ: 資格情報なしでデモ利用者のトークンを払い出す。

    バイパスが無効な環境では 404 を返し、この経路の存在自体を露出しない。
    対象は AUTH_BYPASS_EMAIL のユーザー。未指定なら在籍中の管理者を1件採用し、
    該当者が居なければ払い出さない（フェイルクローズ）。
    """
    if not _auth_bypass_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if settings.AUTH_BYPASS_EMAIL:
        stmt = select(User).where(
            User.email == settings.AUTH_BYPASS_EMAIL, User.is_active.is_(True)
        )
    else:
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.created_at)
            .limit(1)
        )
    user = (await db.execute(stmt)).scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    record_audit(
        db,
        event_type="user.login",
        operation="login",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
        actor_ip=_client_ip(request),
        result="success",
        reason="mvp demo bypass",
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


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DB,
) -> None:
    """Change the current user's password (verifies the current password)."""
    ip = _client_ip(request)
    if not current_user.hashed_password:
        record_audit(
            db,
            event_type="user.password_change_rejected",
            operation="change_password",
            target_type="user",
            target_id=current_user.id,
            actor_id=current_user.id,
            actor_ip=ip,
            result="failure",
            reason="account has no local password (OIDC-only user)",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no local password. Use your identity provider.",
        )

    if not verify_password(body.current_password, current_user.hashed_password):
        record_audit(
            db,
            event_type="user.password_change_failed",
            operation="change_password",
            target_type="user",
            target_id=current_user.id,
            actor_id=current_user.id,
            actor_ip=ip,
            result="failure",
            reason="current password mismatch",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if body.new_password != body.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match",
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    current_user.hashed_password = hash_password(body.new_password)
    record_audit(
        db,
        event_type="user.password_changed",
        operation="change_password",
        target_type="user",
        target_id=current_user.id,
        actor_id=current_user.id,
        actor_ip=ip,
        result="success",
    )
    await db.commit()
