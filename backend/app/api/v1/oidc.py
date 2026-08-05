"""OIDC login endpoints (Authorization Code + PKCE).

Enabled only when OIDC_ENABLED=true and OIDC_ISSUER/CLIENT_ID/SECRET/REDIRECT_URI
are configured. MFA is enforced by the identity provider (conditional access).
"""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DB
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services import oidc as oidc_service
from app.services.audit import record_audit

router = APIRouter(prefix="/auth/oidc", tags=["oidc"])


def _ensure_enabled() -> None:
    if not settings.OIDC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OIDC is not enabled"
        )


@router.get("/config")
async def oidc_config() -> dict:
    return {
        "enabled": settings.OIDC_ENABLED,
        "authorize_url": (
            "/api/v1/auth/oidc/authorize" if settings.OIDC_ENABLED else None
        ),
    }


@router.get("/authorize")
async def oidc_authorize() -> RedirectResponse:
    _ensure_enabled()
    url, _ = await oidc_service.create_authorization_url()
    return RedirectResponse(url)


@router.get("/callback", response_model=TokenResponse)
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    db: DB,
) -> TokenResponse:
    _ensure_enabled()
    try:
        state_payload = oidc_service.decode_oidc_state(state)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state"
        )

    tokens = await oidc_service.exchange_code(code, state_payload["code_verifier"])
    keys = await oidc_service.get_jwks()
    id_claims = oidc_service.verify_id_token_with_keys(tokens["id_token"], keys)
    if id_claims.get("nonce") != state_payload.get("nonce"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nonce mismatch"
        )

    sub = id_claims["sub"]
    email = (id_claims.get("email") or "").lower()
    if not email:
        userinfo = await oidc_service.fetch_userinfo(tokens["access_token"])
        email = (userinfo.get("email") or "").lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IdP did not return an email claim",
        )

    result = await db.execute(
        select(User).where((User.email == email) | (User.oidc_sub == sub))
    )
    user = result.scalars().first()
    if user is None:
        user = User(
            email=email,
            username=email.split("@")[0][:100] or "oidcuser",
            full_name=id_claims.get("name") or email,
            is_active=settings.OIDC_JIT_ACTIVE,
            oidc_sub=sub,
        )
        db.add(user)
        await db.flush()
    elif not user.oidc_sub:
        user.oidc_sub = sub

    if not user.is_active:
        record_audit(
            db,
            event_type="user.oidc_login_rejected",
            operation="login",
            target_type="user",
            target_id=user.id,
            actor_id=user.id,
            actor_ip=request.client.host if request.client else None,
            result="failure",
            reason="account not activated",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated. Contact your administrator.",
        )

    record_audit(
        db,
        event_type="user.oidc_login",
        operation="login",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
        actor_ip=request.client.host if request.client else None,
        result="success",
    )
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )
