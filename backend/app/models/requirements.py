import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentType(str, enum.Enum):
    oir = "OIR"
    air = "AIR"
    pir = "PIR"
    eir = "EIR"
    bep = "BEP"
    midp = "MIDP"
    tidp = "TIDP"
    protocol = "InformationProtocol"
    supplementary = "Supplementary"


class DocumentStatus(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    approved = "approved"
    superseded = "superseded"
    withdrawn = "withdrawn"


class RequirementsDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "requirements_documents"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    revision: Mapped[str] = mapped_column(String(20), nullable=False, default="01")
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.draft
    )
    effective_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["RequirementItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class RequirementItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "requirement_items"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("requirements_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_no: Mapped[str] = mapped_column(String(50), nullable=False)
    # ISO 19650: what / when / how / for_whom
    what: Mapped[str] = mapped_column(Text, nullable=False)
    when_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    how_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    for_whom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    document: Mapped["RequirementsDocument"] = relationship(back_populates="items")
