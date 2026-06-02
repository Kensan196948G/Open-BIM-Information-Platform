from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectNamingRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-project naming rule configuration stored as JSON segments."""

    __tablename__ = "project_naming_rules"
    __table_args__ = (UniqueConstraint("project_id", name="uq_project_naming_rule"),)

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    separator: Mapped[str] = mapped_column(String(10), nullable=False, default="-")
    # List of SegmentDefinition-compatible dicts
    segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    project: Mapped["Project"] = relationship(back_populates="naming_rule")


from app.models.project import Project  # noqa: E402, F401
