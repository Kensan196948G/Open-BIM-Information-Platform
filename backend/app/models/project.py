import enum
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    completed = "completed"
    archived = "archived"


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.active, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    applied_standard: Mapped[str] = mapped_column(
        String(100), default="ISO 19650", nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    containers: Mapped[list["InformationContainer"]] = relationship(
        back_populates="project"
    )
    naming_rule: Mapped["ProjectNamingRule | None"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )


class ProjectMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "project_members"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("roles.id"), nullable=True
    )
    # ISO 19650 contract roles
    contract_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship(back_populates="members")


from app.models.container import InformationContainer  # noqa: E402, F401
from app.models.naming_rule import ProjectNamingRule  # noqa: E402, F401
from app.models.organization import Organization  # noqa: E402, F401
from app.models.role import Role  # noqa: E402, F401
