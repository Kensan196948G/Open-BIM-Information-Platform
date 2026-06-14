from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import DB, CurrentUser
from app.models.project import Project
from app.models.requirements import RequirementItem, RequirementsDocument
from app.models.user import UserOrganization
from app.schemas.requirements import (
    RequirementItemCreate,
    RequirementItemResponse,
    RequirementsDocumentCreate,
    RequirementsDocumentListResponse,
    RequirementsDocumentResponse,
    RequirementsDocumentUpdate,
)

router = APIRouter(tags=["requirements"])


async def _require_project_membership(project_id: str, current_user, db) -> Project:
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


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementsDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirements_document(
    project_id: str,
    body: RequirementsDocumentCreate,
    current_user: CurrentUser,
    db: DB,
) -> RequirementsDocumentResponse:
    await _require_project_membership(project_id, current_user, db)
    doc = RequirementsDocument(
        project_id=project_id,
        owner_user_id=current_user.id,
        **body.model_dump(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return RequirementsDocumentResponse.model_validate(doc)


@router.get(
    "/projects/{project_id}/requirements",
    response_model=RequirementsDocumentListResponse,
)
async def list_requirements_documents(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    doc_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> RequirementsDocumentListResponse:
    await _require_project_membership(project_id, current_user, db)
    q = select(RequirementsDocument).where(
        RequirementsDocument.project_id == project_id
    )
    if doc_type:
        q = q.where(RequirementsDocument.doc_type == doc_type)

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return RequirementsDocumentListResponse(
        items=[RequirementsDocumentResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get(
    "/projects/{project_id}/requirements/{doc_id}",
    response_model=RequirementsDocumentResponse,
)
async def get_requirements_document(
    project_id: str,
    doc_id: str,
    current_user: CurrentUser,
    db: DB,
) -> RequirementsDocumentResponse:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument).where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return RequirementsDocumentResponse.model_validate(doc)


@router.patch(
    "/projects/{project_id}/requirements/{doc_id}",
    response_model=RequirementsDocumentResponse,
)
async def update_requirements_document(
    project_id: str,
    doc_id: str,
    body: RequirementsDocumentUpdate,
    current_user: CurrentUser,
    db: DB,
) -> RequirementsDocumentResponse:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument).where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    await db.commit()
    await db.refresh(doc)
    return RequirementsDocumentResponse.model_validate(doc)


@router.delete(
    "/projects/{project_id}/requirements/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_requirements_document(
    project_id: str,
    doc_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument).where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    await db.delete(doc)
    await db.commit()


@router.post(
    "/projects/{project_id}/requirements/{doc_id}/items",
    response_model=RequirementItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_item(
    project_id: str,
    doc_id: str,
    body: RequirementItemCreate,
    current_user: CurrentUser,
    db: DB,
) -> RequirementItemResponse:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument).where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    item = RequirementItem(document_id=doc_id, **body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return RequirementItemResponse.model_validate(item)


@router.get(
    "/projects/{project_id}/requirements/{doc_id}/items",
    response_model=list[RequirementItemResponse],
)
async def list_requirement_items(
    project_id: str,
    doc_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[RequirementItemResponse]:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument).where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    items_result = await db.execute(
        select(RequirementItem).where(RequirementItem.document_id == doc_id)
    )
    return [
        RequirementItemResponse.model_validate(i) for i in items_result.scalars().all()
    ]
