"""Audit & compliance report API (Issue #51).

Aggregates existing operational data — ``InformationContainer`` /
``ContainerStateHistory``, ``WorkflowInstance`` / ``WorkflowTask``, and
``RequirementsDocument`` / ``RequirementItem`` — into read-only reports for
reviewers and org admins. No new tables are introduced; everything here is
computed on the fly from existing rows.

Access is restricted to ``reports.read`` (reviewer / org_admin and above);
regular members cannot view these reports.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DB, CurrentUser
from app.models.container import ContainerStateHistory, InformationContainer
from app.models.project import Project
from app.models.requirements import ItemStatus, RequirementsDocument
from app.models.user import UserOrganization
from app.models.workflow import WorkflowInstance, WorkflowStatus, WorkflowTask
from app.schemas.reports import (
    ApprovalDelayAssignee,
    ApprovalDelayItem,
    ApprovalDelaysResponse,
    NamingViolationItem,
    NamingViolationsResponse,
    RequirementsStatusItem,
    RequirementsStatusResponse,
)
from app.services.audit import enum_value
from app.services.rbac import P_REPORTS_READ, require_permission

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["reports"])


async def _require_project_membership(project_id: str, current_user, db) -> Project:
    """Return project only if current_user is a member of its organization."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if not current_user.is_platform_admin:
        membership = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == project.organization_id,
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

    return project


@router.get("/naming-violations", response_model=NamingViolationsResponse)
async def get_naming_violations(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
) -> NamingViolationsResponse:
    """Containers that are naming-rule non-compliant or were rejected in review.

    ``current_assignee_id`` is a best-effort proxy: the container's creator,
    who is responsible for correcting it (containers have no dedicated
    assignee field).
    """
    project = await _require_project_membership(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_REPORTS_READ,
    )

    items: list[NamingViolationItem] = []

    # 1) Naming-rule non-compliant containers
    non_compliant = await db.execute(
        select(InformationContainer).where(
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
            InformationContainer.naming_valid.is_(False),
        )
    )
    for container in non_compliant.scalars().all():
        items.append(
            NamingViolationItem(
                container_id=container.id,
                identifier=container.identifier,
                title=container.title,
                violation_type="naming_non_compliant",
                reason=container.naming_issues,
                occurred_at=container.updated_at.isoformat()
                if container.updated_at
                else None,
                current_state=enum_value(container.current_state),
                current_assignee_id=container.created_by,
            )
        )

    # 2) Workflow-rejected containers. A rejection reverts the container to
    # WIP and records a ContainerStateHistory row (action="return") tagged
    # with the workflow_instance_id — that row carries the rejection
    # comment/timestamp we want to surface here.
    rejected_rows = await db.execute(
        select(WorkflowInstance, ContainerStateHistory, InformationContainer)
        .join(
            ContainerStateHistory,
            ContainerStateHistory.workflow_instance_id == WorkflowInstance.id,
        )
        .join(
            InformationContainer,
            InformationContainer.id == WorkflowInstance.target_id,
        )
        .where(
            WorkflowInstance.project_id == project_id,
            WorkflowInstance.target_type == "container",
            WorkflowInstance.status == WorkflowStatus.rejected,
            InformationContainer.is_deleted.is_(False),
        )
    )
    for _workflow, history, container in rejected_rows.all():
        items.append(
            NamingViolationItem(
                container_id=container.id,
                identifier=container.identifier,
                title=container.title,
                violation_type="rejected",
                reason=history.comment,
                occurred_at=history.acted_at,
                current_state=enum_value(container.current_state),
                current_assignee_id=container.created_by,
            )
        )

    return NamingViolationsResponse(items=items, total=len(items))


@router.get("/approval-delays", response_model=ApprovalDelaysResponse)
async def get_approval_delays(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    threshold_hours: float = Query(72.0, gt=0),
) -> ApprovalDelaysResponse:
    """Pending workflows that have exceeded ``threshold_hours`` since creation."""
    project = await _require_project_membership(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_REPORTS_READ,
    )

    cutoff = datetime.now(UTC) - timedelta(hours=threshold_hours)
    result = await db.execute(
        select(WorkflowInstance)
        .where(
            WorkflowInstance.project_id == project_id,
            WorkflowInstance.status == WorkflowStatus.pending,
            WorkflowInstance.created_at <= cutoff,
        )
        .order_by(WorkflowInstance.created_at.asc())
    )
    workflows = result.scalars().all()

    if not workflows:
        return ApprovalDelaysResponse(
            items=[], total=0, threshold_hours=threshold_hours
        )

    workflow_ids = [w.id for w in workflows]
    container_ids = [w.target_id for w in workflows if w.target_type == "container"]

    containers_by_id: dict[str, InformationContainer] = {}
    if container_ids:
        cont_rows = await db.execute(
            select(InformationContainer).where(
                InformationContainer.id.in_(container_ids)
            )
        )
        containers_by_id = {c.id: c for c in cont_rows.scalars().all()}

    tasks_rows = await db.execute(
        select(WorkflowTask).where(WorkflowTask.workflow_id.in_(workflow_ids))
    )
    tasks_by_workflow: dict[str, list[WorkflowTask]] = {}
    for task in tasks_rows.scalars().all():
        tasks_by_workflow.setdefault(task.workflow_id, []).append(task)

    now = datetime.now(UTC)
    items: list[ApprovalDelayItem] = []
    for workflow in workflows:
        container = containers_by_id.get(workflow.target_id)
        created_at = workflow.created_at
        # SQLite (used in unit tests) does not preserve tzinfo on round-trip;
        # normalize to UTC-aware before diffing against `now`.
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        elapsed_hours = round((now - created_at).total_seconds() / 3600, 1)
        items.append(
            ApprovalDelayItem(
                workflow_id=workflow.id,
                workflow_type=workflow.workflow_type,
                target_type=workflow.target_type,
                target_id=workflow.target_id,
                container_identifier=container.identifier if container else None,
                container_title=container.title if container else None,
                created_at=workflow.created_at,
                elapsed_hours=elapsed_hours,
                assignees=[
                    ApprovalDelayAssignee(
                        assignee_id=t.assignee_id,
                        task_type=t.task_type,
                        status=enum_value(t.status),
                    )
                    for t in tasks_by_workflow.get(workflow.id, [])
                ],
            )
        )

    return ApprovalDelaysResponse(
        items=items, total=len(items), threshold_hours=threshold_hours
    )


@router.get("/requirements-status", response_model=RequirementsStatusResponse)
async def get_requirements_status(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
) -> RequirementsStatusResponse:
    """Per-document met/partial/not_met counts and fulfillment rate."""
    project = await _require_project_membership(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_REPORTS_READ,
    )

    result = await db.execute(
        select(RequirementsDocument)
        .where(RequirementsDocument.project_id == project_id)
        .options(selectinload(RequirementsDocument.items))
    )
    docs = result.scalars().all()

    items: list[RequirementsStatusItem] = []
    for doc in docs:
        met = sum(1 for i in doc.items if i.status == ItemStatus.met)
        partial = sum(1 for i in doc.items if i.status == ItemStatus.partial)
        not_met = sum(1 for i in doc.items if i.status == ItemStatus.not_met)
        total_count = len(doc.items)
        fulfillment_rate = round(met / total_count, 4) if total_count else 0.0
        items.append(
            RequirementsStatusItem(
                document_id=doc.id,
                doc_type=enum_value(doc.doc_type),
                title=doc.title,
                revision=doc.revision,
                met_count=met,
                partial_count=partial,
                not_met_count=not_met,
                total_count=total_count,
                fulfillment_rate=fulfillment_rate,
            )
        )

    return RequirementsStatusResponse(items=items, total=len(items))
