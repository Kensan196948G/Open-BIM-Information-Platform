from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DB
from app.models.project import Project, ProjectMember
from app.models.user import UserOrganization
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _require_project_membership(project_id: str, current_user, db) -> Project:
    """Return project only if current_user belongs to its organization."""
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


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> ProjectListResponse:
    offset = (page - 1) * size

    if current_user.is_platform_admin:
        q = select(Project)
    else:
        # Only projects within the user's organizations
        q = (
            select(Project)
            .join(UserOrganization, UserOrganization.organization_id == Project.organization_id)
            .where(UserOrganization.user_id == current_user.id)
        )

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(q.offset(offset).limit(size))
    items = result.scalars().all()
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    db: DB,
) -> ProjectResponse:
    # Require caller to belong to exactly one org (or be platform admin)
    org_result = await db.execute(
        select(UserOrganization).where(UserOrganization.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()

    if not membership and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to an organization to create projects.",
        )

    org_id = membership.organization_id if membership else None
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform admins must specify organization_id.",
        )

    project = Project(organization_id=org_id, **body.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current_user: CurrentUser, db: DB) -> ProjectResponse:
    project = await _require_project_membership(project_id, current_user, db)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: CurrentUser,
    db: DB,
) -> ProjectResponse:
    project = await _require_project_membership(project_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)
