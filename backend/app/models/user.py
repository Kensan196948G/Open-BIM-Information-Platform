from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    oidc_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    organizations: Mapped[list["UserOrganization"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserOrganization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_organizations"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_in_org: Mapped[str] = mapped_column(
        String(50), nullable=False, default="member"
    )
    is_org_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="organizations")
    organization: Mapped["Organization"] = relationship(back_populates="members")


from app.models.organization import Organization  # noqa: E402, F401
