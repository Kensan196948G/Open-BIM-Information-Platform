import uuid

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.container import ContainerFile, ContainerState, InformationContainer
from app.models.project import Project
from app.models.user import UserOrganization
from app.schemas.upload import FileUploadResponse
from app.services import storage as storage_svc

router = APIRouter(
    prefix="/projects/{project_id}/containers/{container_id}", tags=["uploads"]
)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


async def _get_container_or_403(
    project_id: str, container_id: str, current_user, db
) -> InformationContainer:
    """Verify project membership then return container."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if not current_user.is_platform_admin:
        member = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == project.organization_id,
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
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
    return container


@router.post(
    "/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    project_id: str,
    container_id: str,
    file: UploadFile,
    current_user: CurrentUser,
    db: DB,
) -> FileUploadResponse:
    container = await _get_container_or_403(project_id, container_id, current_user, db)

    if container.current_state != ContainerState.wip:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Files can only be uploaded to WIP containers",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    try:
        storage_key, sha256, size = storage_svc.upload_file(
            data=data,
            content_type=file.content_type or "application/octet-stream",
            project_id=project_id,
            container_id=container_id,
            original_filename=file.filename or "unnamed",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {exc}",
        ) from exc

    container_file = ContainerFile(
        id=str(uuid.uuid4()),
        container_id=container_id,
        original_filename=file.filename or "unnamed",
        storage_key=storage_key,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=size,
        checksum_sha256=sha256,
        uploaded_by=current_user.id,
    )
    db.add(container_file)
    await db.commit()
    await db.refresh(container_file)

    return FileUploadResponse(
        id=container_file.id,
        container_id=container_id,
        original_filename=container_file.original_filename,
        storage_key=storage_key,
        content_type=container_file.content_type,
        file_size_bytes=size,
        checksum_sha256=sha256,
        uploaded_by=current_user.id,
        created_at=container_file.created_at.isoformat(),
    )


@router.get("/files/{file_id}/download-url")
async def get_download_url(
    project_id: str,
    container_id: str,
    file_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    await _get_container_or_403(project_id, container_id, current_user, db)
    result = await db.execute(
        select(ContainerFile).where(
            ContainerFile.id == file_id,
            ContainerFile.container_id == container_id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        url = storage_svc.generate_presigned_url(file_record.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {exc}",
        ) from exc

    return {"download_url": url, "expires_in_seconds": 3600}
