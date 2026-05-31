"""Approval workflow API — ISO 19650 check/review/approve stages."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.container import (
    ContainerState,
    ContainerStateHistory,
    InformationContainer,
)
from app.models.project import Project
from app.models.user import UserOrganization
from app.models.workflow import (
    Approval,
    ApprovalResult,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowTask,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class WorkflowStartRequest(BaseModel):
    project_id: str
    target_type: str = "container"
    target_id: str
    workflow_type: str = "state_transition"
    comment: str | None = None
    assignee_ids: list[str] = []


class ApprovalActRequest(BaseModel):
    result: ApprovalResult
    comment: str | None = None


class WorkflowTaskResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    assignee_id: str
    task_type: str
    status: str
    order: int


class ApprovalResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    approval_stage: str
    approver_id: str
    result: str | None
    acted_at: str | None
    comment: str | None


class WorkflowResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    project_id: str
    target_type: str
    target_id: str
    workflow_type: str
    status: str
    initiated_by: str


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _require_project_member(project_id: str, current_user, db) -> Project:
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


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    body: WorkflowStartRequest, current_user: CurrentUser, db: DB
) -> WorkflowResponse:
    await _require_project_member(body.project_id, current_user, db)

    workflow = WorkflowInstance(
        id=str(uuid.uuid4()),
        project_id=body.project_id,
        target_type=body.target_type,
        target_id=body.target_id,
        workflow_type=body.workflow_type,
        status=WorkflowStatus.in_progress,
        initiated_by=current_user.id,
        comment=body.comment,
    )
    db.add(workflow)

    for i, assignee_id in enumerate(body.assignee_ids):
        task = WorkflowTask(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            assignee_id=assignee_id,
            task_type="review",
            status=WorkflowStatus.pending,
            order=i,
        )
        approval = Approval(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            target_type=body.target_type,
            target_id=body.target_id,
            approval_stage=f"stage_{i + 1}",
            approver_id=assignee_id,
        )
        db.add(task)
        db.add(approval)

    await db.commit()
    await db.refresh(workflow)
    return WorkflowResponse.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str, current_user: CurrentUser, db: DB
) -> WorkflowResponse:
    result = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    await _require_project_member(workflow.project_id, current_user, db)
    return WorkflowResponse.model_validate(workflow)


@router.post(
    "/{workflow_id}/approvals/{approval_id}/act", response_model=ApprovalResponse
)
async def act_on_approval(
    workflow_id: str,
    approval_id: str,
    body: ApprovalActRequest,
    current_user: CurrentUser,
    db: DB,
) -> ApprovalResponse:
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workflow_id == workflow_id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found"
        )

    if approval.approver_id != current_user.id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not the assigned approver"
        )

    if approval.result is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Approval already acted on"
        )

    approval.result = body.result
    approval.acted_at = datetime.now(UTC).isoformat()
    approval.comment = body.comment

    # If approved, check whether all approvals in workflow are done
    wf_result = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == workflow_id)
    )
    workflow = wf_result.scalar_one()

    all_approvals = await db.execute(
        select(Approval).where(Approval.workflow_id == workflow_id)
    )
    approvals = all_approvals.scalars().all()
    all_done = all(a.result is not None for a in approvals)
    all_approved = all_done and all(
        a.result == ApprovalResult.approved for a in approvals
    )
    any_rejected = any(a.result == ApprovalResult.rejected for a in approvals)

    if any_rejected:
        workflow.status = WorkflowStatus.rejected
        # Return the container to WIP if it was in Shared
        if workflow.target_type == "container":
            cont_result = await db.execute(
                select(InformationContainer).where(
                    InformationContainer.id == workflow.target_id
                )
            )
            container = cont_result.scalar_one_or_none()
            if container and container.current_state == ContainerState.shared:
                history = ContainerStateHistory(
                    id=str(uuid.uuid4()),
                    container_id=container.id,
                    from_state=container.current_state.value,
                    to_state=ContainerState.wip.value,
                    action="return",
                    acted_by=current_user.id,
                    acted_at=datetime.now(UTC).isoformat(),
                    comment=body.comment,
                    workflow_instance_id=workflow_id,
                )
                container.current_state = ContainerState.wip
                db.add(history)
    elif all_approved:
        workflow.status = WorkflowStatus.completed

    await db.commit()
    await db.refresh(approval)
    return ApprovalResponse.model_validate(approval)
