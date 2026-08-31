"""MinIO / S3-compatible object storage service."""

import base64
import errno
import fcntl
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

_s3_client = None
VERIFIED_DOWNLOAD_MEMORY_LIMIT = 8 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class StorageIntegrityError(Exception):
    """The stored object bytes do not match the database checksum."""


class DownloadTooLargeError(Exception):
    """The object exceeds the configured per-request temporary storage limit."""


class DownloadQuotaExceededError(Exception):
    """The shared temporary storage reservation limit is currently exhausted."""


class DownloadStorageFullError(Exception):
    """The temporary storage filesystem cannot hold the requested object."""


class DownloadBody(Protocol):
    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


def _process_start_ticks(pid: int) -> str | None:
    """Return the Linux process start time used to reject stale PID reuse."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return None
    fields = stat.rsplit(")", 1)
    if len(fields) != 2:
        return None
    remainder = fields[1].split()
    return remainder[19] if len(remainder) > 19 else None


@dataclass
class TemporaryStorageReservation:
    marker: Path

    def release(self) -> None:
        self.marker.unlink(missing_ok=True)


def _reservation_is_active(payload: dict[str, object]) -> bool:
    try:
        pid_value = payload["pid"]
        expected_start = str(payload["start_ticks"])
    except KeyError:
        return False
    if not isinstance(pid_value, (str, int)):
        return False
    try:
        pid = int(pid_value)
    except ValueError:
        return False
    actual_start = _process_start_ticks(pid)
    return actual_start is not None and hmac.compare_digest(
        actual_start, expected_start
    )


def reserve_temporary_storage(size_bytes: int) -> TemporaryStorageReservation:
    """Atomically reserve legacy-download space across local worker processes."""
    if size_bytes < 0 or size_bytes > settings.DOWNLOAD_TEMP_REQUEST_LIMIT_BYTES:
        raise DownloadTooLargeError

    directory = Path(settings.DOWNLOAD_TEMP_DIR)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    lock_path = directory / ".quota.lock"
    process_start = _process_start_ticks(os.getpid())
    if process_start is None:
        raise DownloadStorageFullError

    with lock_path.open("a+", encoding="ascii") as lock_file:
        lock_path.chmod(0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        reserved = 0
        for marker in directory.glob(".reservation-*.json"):
            try:
                payload = json.loads(marker.read_text(encoding="ascii"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                marker.unlink(missing_ok=True)
                continue
            if not isinstance(payload, dict) or not _reservation_is_active(payload):
                marker.unlink(missing_ok=True)
                continue
            try:
                reserved += int(payload["size_bytes"])
            except (KeyError, TypeError, ValueError):
                marker.unlink(missing_ok=True)

        if reserved + size_bytes > settings.DOWNLOAD_TEMP_GLOBAL_LIMIT_BYTES:
            raise DownloadQuotaExceededError
        if shutil.disk_usage(directory).free < size_bytes:
            raise DownloadStorageFullError

        marker = directory / f".reservation-{uuid.uuid4().hex}.json"
        payload = {
            "pid": os.getpid(),
            "start_ticks": process_start,
            "size_bytes": size_bytes,
        }
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as marker_file:
            json.dump(payload, marker_file)
        return TemporaryStorageReservation(marker)


@dataclass
class VerifiedDownload:
    """A response body that closes its storage and quota on every exit path."""

    body: DownloadBody
    expected_sha256: str
    preverified: bool
    reservation: TemporaryStorageReservation | None = None

    def close(self) -> None:
        try:
            self.body.close()
        finally:
            if self.reservation is not None:
                self.reservation.release()
                self.reservation = None

    def iter_chunks(self) -> Iterator[bytes]:
        try:
            if self.preverified:
                while chunk := self.body.read(DOWNLOAD_CHUNK_SIZE):
                    yield chunk
                return

            # Keep one chunk back. Botocore validates a fixed-size streaming
            # response checksum on the empty read after EOF, so look-ahead
            # prevents the final bytes from reaching the client first.
            digest = hashlib.sha256()
            pending = self.body.read(DOWNLOAD_CHUNK_SIZE)
            while pending:
                following = self.body.read(DOWNLOAD_CHUNK_SIZE)
                digest.update(pending)
                if not following and not hmac.compare_digest(
                    digest.hexdigest(), self.expected_sha256
                ):
                    raise StorageIntegrityError("Stored object checksum mismatch")
                yield pending
                pending = following
            if not hmac.compare_digest(digest.hexdigest(), self.expected_sha256):
                raise StorageIntegrityError("Stored object checksum mismatch")
        finally:
            self.close()


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
            config=Config(response_checksum_validation="when_supported"),
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
        ChecksumSHA256=base64.b64encode(bytes.fromhex(sha256)).decode("ascii"),
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


def open_file(storage_key: str) -> dict:
    """Open an object for authenticated API streaming."""
    return get_s3_client().get_object(
        Bucket=settings.MINIO_BUCKET,
        Key=storage_key,
        ChecksumMode="ENABLED",
    )


def open_verified_file(
    storage_key: str, expected_sha256: str, expected_size: int
) -> VerifiedDownload:
    """Open a protocol-checked stream, with a preverified legacy fallback."""
    response = open_file(storage_key)
    body = response["Body"]
    if response.get("ContentLength") != expected_size:
        body.close()
        raise StorageIntegrityError("Stored object size mismatch")

    try:
        expected_base64 = base64.b64encode(bytes.fromhex(expected_sha256)).decode(
            "ascii"
        )
    except ValueError as exc:
        body.close()
        raise StorageIntegrityError("Database checksum is invalid") from exc
    protocol_checksum = response.get("ChecksumSHA256")
    if protocol_checksum:
        if not hmac.compare_digest(protocol_checksum, expected_base64):
            body.close()
            raise StorageIntegrityError("Stored object checksum mismatch")
        return VerifiedDownload(body, expected_sha256, preverified=False)

    metadata_checksum = response.get("Metadata", {}).get("sha256")
    if metadata_checksum and not hmac.compare_digest(
        metadata_checksum, expected_sha256
    ):
        body.close()
        raise StorageIntegrityError("Stored object metadata checksum mismatch")

    try:
        reservation = reserve_temporary_storage(expected_size)
    except Exception:
        body.close()
        raise

    try:
        output = tempfile.SpooledTemporaryFile(
            max_size=VERIFIED_DOWNLOAD_MEMORY_LIMIT,
            dir=settings.DOWNLOAD_TEMP_DIR,
        )
        digest = hashlib.sha256()
        for chunk in body.iter_chunks(chunk_size=DOWNLOAD_CHUNK_SIZE):
            if not chunk:
                continue
            digest.update(chunk)
            output.write(chunk)
    except OSError as exc:
        if "output" in locals():
            output.close()
        reservation.release()
        if exc.errno in {errno.ENOSPC, errno.EDQUOT}:
            raise DownloadStorageFullError from exc
        raise
    except Exception:
        if "output" in locals():
            output.close()
        reservation.release()
        raise
    finally:
        body.close()

    if digest.hexdigest() != expected_sha256:
        output.close()
        reservation.release()
        raise StorageIntegrityError("Stored object checksum mismatch")
    output.seek(0)
    return VerifiedDownload(
        output,
        expected_sha256,
        preverified=True,
        reservation=reservation,
    )


def delete_file(storage_key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.MINIO_BUCKET, Key=storage_key)
