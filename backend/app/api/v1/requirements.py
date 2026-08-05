from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import DB, CurrentUser
from app.models.project import Project
from app.models.requirements import RequirementItem, RequirementsDocument
from app.models.user import UserOrganization
from app.schemas.requirements import (
    RequirementItemCreate,
    RequirementItemResponse,
    RequirementItemUpdate,
    RequirementsDocumentCreate,
    RequirementsDocumentListResponse,
    RequirementsDocumentResponse,
    RequirementsDocumentUpdate,
)
from app.services.audit import enum_value, record_audit

router = APIRouter(tags=["requirements"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


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


def _document_response(doc: RequirementsDocument) -> RequirementsDocumentResponse:
    items = [RequirementItemResponse.model_validate(i) for i in doc.items]
    return RequirementsDocumentResponse(
        id=doc.id,
        project_id=doc.project_id,
        owner_user_id=doc.owner_user_id,
        doc_type=enum_value(doc.doc_type),
        title=doc.title,
        revision=doc.revision,
        status=enum_value(doc.status),
        effective_from=doc.effective_from,
        effective_to=doc.effective_to,
        description=doc.description,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        item_count=len(items),
        items=items,
    )


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementsDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirements_document(
    request: Request,
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
    await db.flush()
    record_audit(
        db,
        event_type="requirements.document_created",
        operation="create",
        target_type="requirements_document",
        target_id=doc.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        after_json={
            "doc_type": enum_value(doc.doc_type),
            "title": doc.title,
            "revision": doc.revision,
            "status": enum_value(doc.status),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(doc, attribute_names=["items"])
    return _document_response(doc)


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
    q = (
        select(RequirementsDocument)
        .where(RequirementsDocument.project_id == project_id)
        .options(selectinload(RequirementsDocument.items))
    )
    if doc_type:
        q = q.where(RequirementsDocument.doc_type == doc_type)

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()
    return RequirementsDocumentListResponse(
        items=[_document_response(d) for d in docs],
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
        select(RequirementsDocument)
        .where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
        .options(selectinload(RequirementsDocument.items))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return _document_response(doc)


@router.patch(
    "/projects/{project_id}/requirements/{doc_id}",
    response_model=RequirementsDocumentResponse,
)
async def update_requirements_document(
    request: Request,
    project_id: str,
    doc_id: str,
    body: RequirementsDocumentUpdate,
    current_user: CurrentUser,
    db: DB,
) -> RequirementsDocumentResponse:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementsDocument)
        .where(
            RequirementsDocument.id == doc_id,
            RequirementsDocument.project_id == project_id,
        )
        .options(selectinload(RequirementsDocument.items))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    before_json = {
        "title": doc.title,
        "revision": doc.revision,
        "status": enum_value(doc.status),
    }
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    record_audit(
        db,
        event_type="requirements.document_updated",
        operation="update",
        target_type="requirements_document",
        target_id=doc.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        before_json=before_json,
        after_json={
            "title": doc.title,
            "revision": doc.revision,
            "status": enum_value(doc.status),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(doc, attribute_names=["items"])
    return _document_response(doc)


@router.delete(
    "/projects/{project_id}/requirements/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_requirements_document(
    request: Request,
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
    record_audit(
        db,
        event_type="requirements.document_deleted",
        operation="delete",
        target_type="requirements_document",
        target_id=doc_id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()


@router.post(
    "/projects/{project_id}/requirements/{doc_id}/items",
    response_model=RequirementItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_item(
    request: Request,
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
    await db.flush()
    record_audit(
        db,
        event_type="requirements.item_created",
        operation="create",
        target_type="requirement_item",
        target_id=item.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        after_json={
            "item_no": item.item_no,
            "what": item.what,
            "status": enum_value(item.status),
        },
        result="success",
    )
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


@router.patch(
    "/projects/{project_id}/requirements/{doc_id}/items/{item_id}",
    response_model=RequirementItemResponse,
)
async def update_requirement_item(
    request: Request,
    project_id: str,
    doc_id: str,
    item_id: str,
    body: RequirementItemUpdate,
    current_user: CurrentUser,
    db: DB,
) -> RequirementItemResponse:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementItem).where(
            RequirementItem.id == item_id,
            RequirementItem.document_id == doc_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requirement item not found"
        )

    before_json = {
        "item_no": item.item_no,
        "what": item.what,
        "status": enum_value(item.status),
    }
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        event_type="requirements.item_updated",
        operation="update",
        target_type="requirement_item",
        target_id=item.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        before_json=before_json,
        after_json={
            "item_no": item.item_no,
            "what": item.what,
            "status": enum_value(item.status),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(item)
    return RequirementItemResponse.model_validate(item)


@router.delete(
    "/projects/{project_id}/requirements/{doc_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_requirement_item(
    request: Request,
    project_id: str,
    doc_id: str,
    item_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    await _require_project_membership(project_id, current_user, db)
    result = await db.execute(
        select(RequirementItem).where(
            RequirementItem.id == item_id,
            RequirementItem.document_id == doc_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requirement item not found"
        )
    await db.delete(item)
    record_audit(
        db,
        event_type="requirements.item_deleted",
        operation="delete",
        target_type="requirement_item",
        target_id=item_id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()
