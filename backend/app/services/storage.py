"""MinIO / S3-compatible object storage service."""

import hashlib
import io
import re
import tempfile
import uuid
from pathlib import PurePosixPath

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

_s3_client = None
VERIFIED_DOWNLOAD_MEMORY_LIMIT = 8 * 1024 * 1024


class StorageIntegrityError(Exception):
    """The stored object bytes do not match the database checksum."""


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        protocol = "https" if settings.MINIO_SECURE else "http"
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"{protocol}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
    return _s3_client


def ensure_bucket_exists(bucket: str = settings.MINIO_BUCKET) -> None:
    """Called once at startup via lifespan — not per request."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def check_storage(bucket: str = settings.MINIO_BUCKET) -> None:
    """Raise when the configured bucket is not reachable."""
    get_s3_client().head_bucket(Bucket=bucket)


def _safe_ext(filename: str) -> str:
    """Return a sanitized, allowlisted extension (alphanumeric only, ≤10 chars)."""
    suffix = PurePosixPath(filename).suffix.lstrip(".")
    return re.sub(r"[^a-zA-Z0-9]", "", suffix)[:10] or "bin"


def upload_file(
    data: bytes,
    content_type: str,
    project_id: str,
    container_id: str,
    original_filename: str,
) -> tuple[str, str, int]:
    """Upload file bytes to MinIO. Returns (storage_key, sha256_hex, size_bytes)."""
    sha256 = hashlib.sha256(data).hexdigest()
    ext = _safe_ext(original_filename)
    storage_key = f"{project_id}/{container_id}/{uuid.uuid4().hex}.{ext}"

    get_s3_client().put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=storage_key,
        Body=io.BytesIO(data),
        ContentType=content_type,
        ContentLength=len(data),
        Metadata={"original-filename": original_filename[:255], "sha256": sha256},
    )
    return storage_key, sha256, len(data)


def generate_presigned_url(
    storage_key: str,
    original_filename: str = "download",
    expires_in: int = 3600,
) -> str:
    """Generate a presigned download URL that forces browser download (Content-Disposition: attachment)."""
    # Sanitize filename for Content-Disposition header
    safe_name = re.sub(r"[^\w.\-]", "_", original_filename)[:200]
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.MINIO_BUCKET,
            "Key": storage_key,
            "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
            "ResponseContentType": "application/octet-stream",
        },
        ExpiresIn=expires_in,
    )


def open_file(storage_key: str):
    """Open an object for authenticated API streaming."""
    response = get_s3_client().get_object(Bucket=settings.MINIO_BUCKET, Key=storage_key)
    return response["Body"]


def open_verified_file(
    storage_key: str, expected_sha256: str
) -> tempfile.SpooledTemporaryFile[bytes]:
    """Download to bounded-memory temporary storage and verify before serving."""
    body = open_file(storage_key)
    output = tempfile.SpooledTemporaryFile(max_size=VERIFIED_DOWNLOAD_MEMORY_LIMIT)
    digest = hashlib.sha256()
    try:
        for chunk in body.iter_chunks(chunk_size=1024 * 1024):
            if not chunk:
                continue
            digest.update(chunk)
            output.write(chunk)
    except Exception:
        output.close()
        raise
    finally:
        body.close()

    if digest.hexdigest() != expected_sha256:
        output.close()
        raise StorageIntegrityError("Stored object checksum mismatch")
    output.seek(0)
    return output


def delete_file(storage_key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.MINIO_BUCKET, Key=storage_key)
