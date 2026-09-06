from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ShareRequestStatusValues = (
    str  # "pending" | "approved" | "rejected" | "revoked" | "expired"
)


class ShareRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class ShareRequestApprove(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class ShareRequestReject(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class ShareRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    container_id: str
    requested_by_user_id: str
    approved_by_user_id: str | None
    reason: str | None
    status: str
    # The token itself is intentionally never included here — only the
    # requester/approver-facing metadata is returned. The token is handed
    # back once, at approval time, via ShareRequestApproveResponse.
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShareRequestApproveResponse(ShareRequestResponse):
    token: str
    share_url_path: str


class ShareRequestListResponse(BaseModel):
    items: list[ShareRequestResponse]
    total: int
