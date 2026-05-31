import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
