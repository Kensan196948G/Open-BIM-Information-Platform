import re
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.container import ContainerFile, ContainerState, InformationContainer
from app.models.project import Project
from app.models.user import UserOrganization
from app.schemas.upload import FileUploadResponse
from app.services import storage as storage_svc
from app.services.audit import enum_value, record_audit

router = APIRouter(
    prefix="/projects/{project_id}/containers/{container_id}", tags=["uploads"]
)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk

# Allowlisted MIME types — excludes renderable types to prevent Stored XSS
ALLOWED_CONTENT_TYPES = {
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/json",
    "application/xml",
    "text/plain",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "model/ifc",
    "application/x-step",
    "application/acad",
    "image/vnd.dwg",
    "image/x-dwg",
    "application/dxf",
    "model/vnd.obj",
    "model/gltf+json",
    "model/gltf-binary",
    # IFC and BIM formats
    "application/ifc",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Extension allowlist (after sanitization)
ALLOWED_EXTENSIONS = {
    "pdf",
    "ifc",
    "ifczip",
    "bcf",
    "bcfzip",
    "zip",
    "xlsx",
    "xls",
    "docx",
    "doc",
    "pptx",
    "ppt",
    "png",
    "jpg",
    "jpeg",
    "tif",
    "tiff",
    "bmp",
    "csv",
    "txt",
    "json",
    "xml",
    "dwg",
    "dxf",
    "rvt",
    "rfa",
    "skp",
    "obj",
    "gltf",
    "glb",
}


def _sanitize_extension(filename: str) -> str:
    """Extract and sanitize file extension — alphanumeric only, allowlisted."""
    suffix = PurePosixPath(filename).suffix.lstrip(".")
    clean = re.sub(r"[^a-zA-Z0-9]", "", suffix)[:10].lower()
    return clean if clean in ALLOWED_EXTENSIONS else "bin"


async def _read_streaming(file: UploadFile) -> bytes:
    """Stream file in chunks, raising 413 before loading >MAX_FILE_SIZE into memory."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _get_container_or_403(
    project_id: str, container_id: str, current_user, db
) -> InformationContainer:
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
    request: Request,
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

    # Validate MIME type against allowlist (defense against Stored XSS)
    declared_ct = (
        (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    )
    if declared_ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content-Type '{declared_ct}' is not permitted. Upload BIM/document files only.",
        )

    # Stream-read with early abort on size limit
    data = await _read_streaming(file)

    ext = _sanitize_extension(file.filename or "unnamed")

    try:
        storage_key, sha256, size = storage_svc.upload_file(
            data=data,
            # Always store as octet-stream — presigned URL forces download attachment
            content_type="application/octet-stream",
            project_id=project_id,
            container_id=container_id,
            original_filename=f"{uuid.uuid4().hex}.{ext}",
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
        content_type="application/octet-stream",
        file_size_bytes=size,
        checksum_sha256=sha256,
        uploaded_by=current_user.id,
    )
    db.add(container_file)
    record_audit(
        db,
        event_type="file.uploaded",
        operation="upload",
        target_type="container",
        target_id=container_id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        after_json={
            "file_id": container_file.id,
            "original_filename": container_file.original_filename,
            "size_bytes": container_file.file_size_bytes,
            "sha256": container_file.checksum_sha256,
            "container_state": enum_value(container.current_state),
        },
        result="success",
    )
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
        # Force download (Content-Disposition: attachment) to prevent Stored XSS
        url = storage_svc.generate_presigned_url(
            file_record.storage_key,
            original_filename=file_record.original_filename,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {exc}",
        ) from exc

    return {"download_url": url, "expires_in_seconds": 3600}
