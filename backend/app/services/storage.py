"""MinIO / S3-compatible object storage service."""

import hashlib
import io
import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

_s3_client = None


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
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def upload_file(
    data: bytes,
    content_type: str,
    project_id: str,
    container_id: str,
    original_filename: str,
) -> tuple[str, str, int]:
    """Upload file to MinIO. Returns (storage_key, sha256_hex, size_bytes)."""
    ensure_bucket_exists()
    sha256 = hashlib.sha256(data).hexdigest()
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "bin"
    storage_key = f"{project_id}/{container_id}/{uuid.uuid4().hex}.{ext}"

    get_s3_client().put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=storage_key,
        Body=io.BytesIO(data),
        ContentType=content_type,
        ContentLength=len(data),
        Metadata={"original-filename": original_filename, "sha256": sha256},
    )
    return storage_key, sha256, len(data)


def generate_presigned_url(storage_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL."""
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": storage_key},
        ExpiresIn=expires_in,
    )


def delete_file(storage_key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.MINIO_BUCKET, Key=storage_key)
