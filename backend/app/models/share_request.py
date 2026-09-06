import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ShareRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    revoked = "revoked"
    expired = "expired"


class ShareRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """External-share request for an ``InformationContainer``.

    A member requests a time-limited external share link; a reviewer (or
    higher) approves or rejects the request. On approval, a cryptographically
    random ``token`` is issued together with an ``expires_at`` timestamp. The
    token is the only credential needed to hit the public (unauthenticated)
    download endpoint, so it must never be logged or exposed in list
    responses beyond what the requester/approver already knows.
    """

    __tablename__ = "share_requests"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("information_containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ShareRequestStatus] = mapped_column(
        Enum(ShareRequestStatus), nullable=False, default=ShareRequestStatus.pending
    )
    token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
