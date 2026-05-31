import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ContainerState(str, enum.Enum):
    wip = "WIP"
    shared = "Shared"
    published = "Published"
    archived = "Archived"


class ContainerType(str, enum.Enum):
    document = "document"
    drawing = "drawing"
    model = "model"
    ifc = "ifc"
    bcf = "bcf"
    other = "other"


class SecurityLevel(str, enum.Enum):
    public = "public"
    limited = "limited"
    confidential = "confidential"
    restricted = "restricted"


class InformationContainer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "information_containers"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    # Core identifier (naming rule compliant)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    container_type: Mapped[ContainerType] = mapped_column(
        Enum(ContainerType), nullable=False, default=ContainerType.document
    )

    # CDE state
    current_state: Mapped[ContainerState] = mapped_column(
        Enum(ContainerState), nullable=False, default=ContainerState.wip
    )

    # Revision: P01, C01 etc. Branch: P01.01 for WIP sub-versions
    current_revision: Mapped[str] = mapped_column(
        String(20), nullable=False, default="P01"
    )
    current_branch: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Classification / security
    classification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    security_level: Mapped[SecurityLevel] = mapped_column(
        Enum(SecurityLevel), nullable=False, default=SecurityLevel.limited
    )

    # Name validation
    naming_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    naming_issues: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship(back_populates="containers")
    files: Mapped[list["ContainerFile"]] = relationship(
        back_populates="container", cascade="all, delete-orphan"
    )
    revisions: Mapped[list["ContainerRevision"]] = relationship(
        back_populates="container", cascade="all, delete-orphan"
    )
    state_histories: Mapped[list["ContainerStateHistory"]] = relationship(
        back_populates="container", cascade="all, delete-orphan"
    )


class ContainerFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "container_files"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("information_containers.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("container_revisions.id"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    container: Mapped["InformationContainer"] = relationship(back_populates="files")


class ContainerRevision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "container_revisions"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("information_containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # No FK constraint to avoid circular dependency with container_files;
    # use container_files.revision_id for the reverse lookup instead.
    file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision_code: Mapped[str] = mapped_column(String(20), nullable=False)
    version_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    container: Mapped["InformationContainer"] = relationship(back_populates="revisions")


class ContainerStateHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "container_state_histories"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("information_containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    acted_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    acted_at: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    container: Mapped["InformationContainer"] = relationship(
        back_populates="state_histories"
    )


from app.models.project import Project  # noqa: E402, F401
