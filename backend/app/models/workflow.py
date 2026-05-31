import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"


class ApprovalResult(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    returned = "returned"
    conditionally_approved = "conditionally_approved"


class WorkflowInstance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_instances"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.pending
    )
    initiated_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    tasks: Mapped[list["WorkflowTask"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship(back_populates="workflow")


class WorkflowTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_tasks"

    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.pending
    )
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    order: Mapped[int] = mapped_column(default=0, nullable=False)

    workflow: Mapped["WorkflowInstance"] = relationship(back_populates="tasks")


class Approval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approvals"

    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approval_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    result: Mapped[ApprovalResult | None] = mapped_column(
        Enum(ApprovalResult), nullable=True
    )
    acted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow: Mapped["WorkflowInstance"] = relationship(back_populates="approvals")
