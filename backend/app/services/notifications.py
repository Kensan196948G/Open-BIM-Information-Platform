"""In-app notification helpers."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User


async def get_user_email(db: AsyncSession, user_id: str) -> str | None:
    """Look up a user's email address (for the optional SMTP side-channel)."""
    result = await db.execute(select(User.email).where(User.id == user_id))
    return result.scalar_one_or_none()


def notify_user(
    db: AsyncSession,
    *,
    user_id: str,
    event_type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> None:
    """Queue an in-app notification on the active session (committed by caller)."""
    db.add(
        Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            title=title,
            body=body,
            link=link,
            is_read=False,
        )
    )
