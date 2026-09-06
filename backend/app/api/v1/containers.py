import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.core.deps import DB, CurrentUser
from app.models.container import (
    ContainerFile,
    ContainerRevision,
    ContainerState,
    ContainerStateHistory,
    InformationContainer,
)
from app.models.naming_rule import ProjectNamingRule
from app.models.project import Project
from app.models.user import UserOrganization
from app.schemas.container import (
    ContainerCreate,
    ContainerListResponse,
    ContainerResponse,
    ContainerUpdate,
    StateTransitionRequest,
)
from app.services.audit import enum_value, record_audit
from app.services.mail import send_mail_safe
from app.services.naming_validator import (
    NamingRule,
    SegmentDefinition,
    _default_iso19650_rule,
    validate_identifier,
)
from app.services.notifications import get_user_email, notify_user
from app.services.rbac import (
    P_CONTAINER_APPROVE,
    P_CONTAINER_ARCHIVE,
    P_CONTAINER_CREATE,
    P_CONTAINER_RETURN,
    P_CONTAINER_REVISE,
    P_CONTAINER_SUBMIT,
    P_CONTAINER_UPDATE,
    require_permission,
)

router = APIRouter(prefix="/projects/{project_id}/containers", tags=["containers"])

# Allowed state transitions: (from_state, action) -> to_state
VALID_TRANSITIONS: dict[tuple[ContainerState, str], ContainerState] = {
    (ContainerState.wip, "submit"): ContainerState.shared,
    (ContainerState.shared, "approve"): ContainerState.published,
    (ContainerState.shared, "return"): ContainerState.wip,
    (ContainerState.published, "revise"): ContainerState.wip,
    (ContainerState.published, "archive"): ContainerState.archived,
    (ContainerState.shared, "archive"): ContainerState.archived,
}

TRANSITION_PERMISSIONS: dict[tuple[ContainerState, str], str] = {
    (ContainerState.wip, "submit"): P_CONTAINER_SUBMIT,
    (ContainerState.shared, "approve"): P_CONTAINER_APPROVE,
    (ContainerState.shared, "return"): P_CONTAINER_RETURN,
    (ContainerState.published, "revise"): P_CONTAINER_REVISE,
    (ContainerState.published, "archive"): P_CONTAINER_ARCHIVE,
    (ContainerState.shared, "archive"): P_CONTAINER_ARCHIVE,
}


async def _get_project_or_404(project_id: str, current_user, db) -> Project:
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


@router.get("", response_model=ContainerListResponse)
async def list_containers(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    state: ContainerState | None = None,
    q: str | None = Query(None, max_length=200),
) -> ContainerListResponse:
    await _get_project_or_404(project_id, current_user, db)
    query = select(InformationContainer).where(
        InformationContainer.project_id == project_id,
        InformationContainer.is_deleted.is_(False),
    )
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            InformationContainer.identifier.ilike(like)
            | InformationContainer.title.ilike(like)
        )
    if state:
        query = query.where(InformationContainer.current_state == state)
    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return ContainerListResponse(
        items=[ContainerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        size=size,
    )


async def _resolve_naming_rule(project_id: str, db) -> NamingRule:
    """Return project-specific naming rule or ISO 19650 default."""
    result = await db.execute(
        select(ProjectNamingRule).where(ProjectNamingRule.project_id == project_id)
    )
    db_rule = result.scalar_one_or_none()
    if not db_rule:
        return _default_iso19650_rule(project_id)
    return NamingRule(
        project_id=project_id,
        separator=db_rule.separator,
        segments=[
            SegmentDefinition(
                key=s["key"],
                label=s.get("label", s["key"]),
                required=s.get("required", True),
                max_length=s.get("max_length"),
                min_length=s.get("min_length"),
                allowed_values=s.get("allowed_values", []),
                pattern=s.get("pattern"),
                description=s.get("description", ""),
            )
            for s in db_rule.segments
        ],
    )


async def _ensure_unique_identifier(
    project_id: str, identifier: str, db, exclude_container_id: str | None = None
) -> None:
    """Reject duplicate identifiers within a project (excluding self on update)."""
    q = select(InformationContainer).where(
        InformationContainer.project_id == project_id,
        InformationContainer.identifier == identifier,
        InformationContainer.is_deleted.is_(False),
    )
    if exclude_container_id:
        q = q.where(InformationContainer.id != exclude_container_id)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Container identifier '{identifier}' already exists in this project",
        )


@router.post("", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_container(
    request: Request,
    project_id: str,
    body: ContainerCreate,
    current_user: CurrentUser,
    db: DB,
) -> ContainerResponse:
    project = await _get_project_or_404(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_CONTAINER_CREATE,
    )

    naming_rule = await _resolve_naming_rule(project_id, db)
    validation = validate_identifier(body.identifier, naming_rule)
    await _ensure_unique_identifier(project_id, body.identifier, db)

    container = InformationContainer(
        project_id=project_id,
        owner_org_id=project.organization_id,
        created_by=current_user.id,
        naming_valid=validation.is_compliant,
        naming_issues=validation.issues_text or None,
        **body.model_dump(),
    )
    db.add(container)
    await db.flush()
    record_audit(
        db,
        event_type="container.created",
        operation="create",
        target_type="container",
        target_id=container.id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        after_json={
            "identifier": container.identifier,
            "title": container.title,
            "container_type": enum_value(container.container_type),
            "current_state": enum_value(container.current_state),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    project_id: str, container_id: str, current_user: CurrentUser, db: DB
) -> ContainerResponse:
    await _get_project_or_404(project_id, current_user, db)
    result = await db.execute(
        select(InformationContainer).where(
            InformationContainer.id == container_id,
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
        )
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Container not found"
        )
    return ContainerResponse.model_validate(container)


@router.get("/{container_id}/revisions")
async def list_container_revisions(
    project_id: str,
    container_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[dict]:
    """Return revision history (with linked file metadata) for a container."""
    await _get_project_or_404(project_id, current_user, db)
    result = await db.execute(
        select(InformationContainer).where(
            InformationContainer.id == container_id,
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Container not found"
        )
    rows = await db.execute(
        select(ContainerRevision, ContainerFile)
        .outerjoin(
            ContainerFile,
            ContainerFile.id == ContainerRevision.file_id,
        )
        .where(ContainerRevision.container_id == container_id)
        .order_by(ContainerRevision.created_at.desc())
    )
    return [
        {
            "id": revision.id,
            "revision_code": revision.revision_code,
            "version_code": revision.version_code,
            "change_reason": revision.change_reason,
            "change_summary": revision.change_summary,
            "created_by": revision.created_by,
            "created_at": revision.created_at.isoformat()
            if revision.created_at
            else None,
            "file": {
                "id": file.id,
                "original_filename": file.original_filename,
                "file_size_bytes": file.file_size_bytes,
                "checksum_sha256": file.checksum_sha256,
            }
            if file
            else None,
        }
        for revision, file in rows.all()
    ]


@router.post("/{container_id}/transition", response_model=ContainerResponse)
async def transition_state(
    request: Request,
    project_id: str,
    container_id: str,
    body: StateTransitionRequest,
    current_user: CurrentUser,
    db: DB,
    background_tasks: BackgroundTasks,
) -> ContainerResponse:
    project = await _get_project_or_404(project_id, current_user, db)
    # Lock the container row to serialize with the workflow reject/revert path
    result = await db.execute(
        select(InformationContainer)
        .where(
            InformationContainer.id == container_id,
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
        )
        .with_for_update()
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Container not found"
        )

    permission_code = TRANSITION_PERMISSIONS.get((container.current_state, body.action))
    if permission_code is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid transition: {container.current_state} + action '{body.action}'",
        )
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=permission_code,
    )

    # Compute next state from the freshly-locked current state
    key = (container.current_state, body.action)
    next_state = VALID_TRANSITIONS.get(key)
    if not next_state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid transition: {container.current_state} + action '{body.action}'",
        )

    # If the client declared an expected target, verify it matches the server's computation
    if body.target_state is not None and body.target_state != next_state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"target_state mismatch: action '{body.action}' yields {next_state.value}, not {body.target_state.value}",
        )

    history = ContainerStateHistory(
        id=str(uuid.uuid4()),
        container_id=container.id,
        from_state=container.current_state.value,
        to_state=next_state.value,
        action=body.action,
        acted_by=current_user.id,
        acted_at=datetime.now(UTC).isoformat(),
        comment=body.comment,
    )
    container.current_state = next_state
    db.add(history)
    if next_state in (ContainerState.published, ContainerState.archived) or (
        next_state == ContainerState.wip and body.action == "return"
    ):
        notif_title = f"コンテナ状態が変更されました（{next_state.value}）"
        notif_body = f"{container.identifier}: action={body.action}"
        notify_user(
            db,
            user_id=container.created_by,
            event_type="container.state_changed",
            title=notif_title,
            body=notif_body,
            link=f"/projects/{project_id}/containers/{container.id}",
        )
        to_email = await get_user_email(db, container.created_by)
        if to_email:
            background_tasks.add_task(
                send_mail_safe,
                to_email=to_email,
                subject=notif_title,
                body=notif_body,
            )
    record_audit(
        db,
        event_type="container.state_changed",
        operation="transition",
        target_type="container",
        target_id=container.id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        before_json={"current_state": history.from_state},
        after_json={"current_state": history.to_state, "action": body.action},
        reason=body.comment,
        result="success",
        workflow_instance_id=None,
    )
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)


@router.patch("/{container_id}", response_model=ContainerResponse)
async def update_container(
    request: Request,
    project_id: str,
    container_id: str,
    body: ContainerUpdate,
    current_user: CurrentUser,
    db: DB,
) -> ContainerResponse:
    project = await _get_project_or_404(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_CONTAINER_UPDATE,
    )
    result = await db.execute(
        select(InformationContainer).where(
            InformationContainer.id == container_id,
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
        )
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Container not found"
        )
    if container.current_state != ContainerState.wip:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only WIP containers can be updated",
        )
    before_json = {
        "title": container.title,
        "security_level": enum_value(container.security_level),
    }
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(container, field, value)
    record_audit(
        db,
        event_type="container.updated",
        operation="update",
        target_type="container",
        target_id=container.id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        before_json=before_json,
        after_json={
            "title": container.title,
            "security_level": enum_value(container.security_level),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)
