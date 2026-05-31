import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DB
from app.models.container import (
    ContainerState,
    ContainerStateHistory,
    InformationContainer,
)
from app.models.project import Project
from app.models.user import UserOrganization
from app.schemas.container import (
    ContainerCreate,
    ContainerListResponse,
    ContainerResponse,
    ContainerUpdate,
    StateTransitionRequest,
)

router = APIRouter(prefix="/projects/{project_id}/containers", tags=["containers"])

# Allowed state transitions: (from_state, action) -> to_state
VALID_TRANSITIONS: dict[tuple[ContainerState, str], ContainerState] = {
    (ContainerState.wip, "submit"): ContainerState.shared,
    (ContainerState.shared, "approve"): ContainerState.published,
    (ContainerState.shared, "return"): ContainerState.wip,
    (ContainerState.published, "archive"): ContainerState.archived,
    (ContainerState.shared, "archive"): ContainerState.archived,
}


async def _get_project_or_404(project_id: str, current_user, db) -> Project:
    """Return project only if current_user is a member of its organization."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not current_user.is_platform_admin:
        membership = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == project.organization_id,
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return project


@router.get("", response_model=ContainerListResponse)
async def list_containers(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    state: ContainerState | None = None,
) -> ContainerListResponse:
    await _get_project_or_404(project_id, current_user, db)
    q = select(InformationContainer).where(
        InformationContainer.project_id == project_id,
        InformationContainer.is_deleted.is_(False),
    )
    if state:
        q = q.where(InformationContainer.current_state == state)
    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return ContainerListResponse(
        items=[ContainerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_container(
    project_id: str,
    body: ContainerCreate,
    current_user: CurrentUser,
    db: DB,
) -> ContainerResponse:
    await _get_project_or_404(project_id, current_user, db)
    org_result = await db.execute(select(Project).where(Project.id == project_id))
    project = org_result.scalar_one()

    container = InformationContainer(
        project_id=project_id,
        owner_org_id=project.organization_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(container)
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    project_id: str, container_id: str, current_user: CurrentUser, db: DB
) -> ContainerResponse:
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


@router.post("/{container_id}/transition", response_model=ContainerResponse)
async def transition_state(
    project_id: str,
    container_id: str,
    body: StateTransitionRequest,
    current_user: CurrentUser,
    db: DB,
) -> ContainerResponse:
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

    key = (container.current_state, body.action)
    next_state = VALID_TRANSITIONS.get(key)
    if not next_state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid transition: {container.current_state} + action '{body.action}'",
        )

    history = ContainerStateHistory(
        id=str(uuid.uuid4()),
        container_id=container.id,
        from_state=container.current_state.value,
        to_state=next_state.value,
        action=body.action,
        acted_by=current_user.id,
        acted_at=datetime.now(timezone.utc).isoformat(),
        comment=body.comment,
    )
    container.current_state = next_state
    db.add(history)
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)


@router.patch("/{container_id}", response_model=ContainerResponse)
async def update_container(
    project_id: str,
    container_id: str,
    body: ContainerUpdate,
    current_user: CurrentUser,
    db: DB,
) -> ContainerResponse:
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
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(container, field, value)
    await db.commit()
    await db.refresh(container)
    return ContainerResponse.model_validate(container)
