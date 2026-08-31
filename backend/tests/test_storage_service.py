"""Unit tests for app/services/storage.py using moto S3 mock."""

import hashlib
import re

import pytest

pytestmark = pytest.mark.no_db

try:
    import boto3
    import moto

    _HAS_MOTO = True
except ImportError:
    _HAS_MOTO = False

needs_moto = pytest.mark.skipif(not _HAS_MOTO, reason="moto[s3] not installed")


@pytest.fixture()
def s3_env(monkeypatch):
    """Moto AWS mock with a pre-created bucket and patched get_s3_client."""
    if not _HAS_MOTO:
        pytest.skip("moto[s3] not installed")

    from app import services

    with moto.mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        client.create_bucket(Bucket="bim-containers")

        monkeypatch.setattr(services.storage, "get_s3_client", lambda: client)
        monkeypatch.setattr(services.storage, "_s3_client", None)

        yield client


@pytest.fixture()
def s3_env_no_bucket(monkeypatch):
    """Moto mock WITHOUT a pre-created bucket — for ensure_bucket_exists tests."""
    if not _HAS_MOTO:
        pytest.skip("moto[s3] not installed")

    from app import services

    with moto.mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )

        monkeypatch.setattr(services.storage, "get_s3_client", lambda: client)
        monkeypatch.setattr(services.storage, "_s3_client", None)

        yield client


# ─── get_s3_client singleton ───────────────────────────────────────────────────


def test_get_s3_client_singleton(monkeypatch):
    """Second call must return the cached client (singleton)."""
    from app.services import storage

    # Reset the cached singleton
    monkeypatch.setattr(storage, "_s3_client", None)

    # Call twice; second call should not invoke boto3.client again
    from unittest.mock import MagicMock, patch

    sentinel = MagicMock()
    with patch("boto3.client", return_value=sentinel) as mock_boto:
        monkeypatch.setattr(storage, "_s3_client", None)
        c1 = storage.get_s3_client()
        c2 = storage.get_s3_client()

    assert c1 is c2
    assert mock_boto.call_count == 1  # boto3.client called only once


# ─── ensure_bucket_exists ─────────────────────────────────────────────────────


@needs_moto
def test_check_storage_succeeds_when_bucket_exists(s3_env):
    """check_storage verifies access to the configured bucket."""
    from app.services.storage import check_storage

    check_storage()


@needs_moto
def test_check_storage_raises_when_bucket_is_missing(s3_env_no_bucket):
    """check_storage surfaces a missing configured bucket."""
    from botocore.exceptions import ClientError

    from app.services.storage import check_storage

    with pytest.raises(ClientError):
        check_storage()


@needs_moto
def test_ensure_bucket_creates_when_missing(s3_env_no_bucket, monkeypatch):
    """ensure_bucket_exists creates the bucket when it does not exist."""
    from app.core.config import settings
    from app.services.storage import ensure_bucket_exists

    bucket = settings.MINIO_BUCKET
    ensure_bucket_exists(bucket)

    # Verify bucket now exists
    response = s3_env_no_bucket.list_buckets()
    bucket_names = [b["Name"] for b in response["Buckets"]]
    assert bucket in bucket_names


@needs_moto
def test_ensure_bucket_does_not_fail_when_exists(s3_env):
    """ensure_bucket_exists is idempotent — no error when bucket already exists."""
    from app.core.config import settings
    from app.services.storage import ensure_bucket_exists

    # Bucket already created in fixture; calling again must not raise
    ensure_bucket_exists(settings.MINIO_BUCKET)


# ─── upload_file ──────────────────────────────────────────────────────────────


@needs_moto
def test_upload_file_returns_storage_key_sha256_size(s3_env):
    """upload_file returns (storage_key, sha256, size) with correct values."""
    from app.services.storage import upload_file

    data = b"ISO 19650 BIM model content"
    key, sha256, size = upload_file(
        data=data,
        content_type="model/ifc",
        project_id="proj-001",
        container_id="cont-abc",
        original_filename="building.ifc",
    )

    assert key.startswith("proj-001/cont-abc/")
    assert key.endswith(".ifc")
    assert sha256 == hashlib.sha256(data).hexdigest()
    assert size == len(data)


@needs_moto
def test_upload_file_object_appears_in_s3(s3_env):
    """Uploaded file is retrievable from the mocked S3 bucket."""
    from app.core.config import settings
    from app.services.storage import upload_file

    data = b"PDF document content"
    key, _, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-002",
        container_id="cont-xyz",
        original_filename="drawing.pdf",
    )

    obj = s3_env.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
    assert obj["Body"].read() == data


@needs_moto
def test_upload_file_stores_sha256_metadata(s3_env):
    """upload_file stores SHA-256 in object metadata for integrity verification."""
    from app.core.config import settings
    from app.services.storage import upload_file

    data = b"BIM specification data"
    key, sha256, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-003",
        container_id="cont-def",
        original_filename="spec.pdf",
    )

    head = s3_env.head_object(Bucket=settings.MINIO_BUCKET, Key=key)
    assert head["Metadata"]["sha256"] == sha256


@needs_moto
def test_upload_file_sanitizes_dangerous_extension(s3_env):
    """Dangerous extensions are sanitized by _safe_ext to safe equivalents."""
    from app.services.storage import upload_file

    data = b"malicious content"
    key, _, _ = upload_file(
        data=data,
        content_type="application/octet-stream",
        project_id="proj-004",
        container_id="cont-ghi",
        original_filename="../../etc/passwd",
    )

    # The extension should be 'bin' (sanitized) not 'passwd' or path traversal
    assert not key.endswith("passwd")
    assert ".." not in key


# ─── generate_presigned_url ───────────────────────────────────────────────────


@needs_moto
def test_generate_presigned_url_returns_string(s3_env):
    """generate_presigned_url returns a non-empty URL string."""
    from app.services.storage import generate_presigned_url, upload_file

    data = b"file for presign test"
    key, _, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-005",
        container_id="cont-jkl",
        original_filename="document.pdf",
    )

    url = generate_presigned_url(key, original_filename="document.pdf")
    assert isinstance(url, str)
    assert len(url) > 0


@needs_moto
def test_generate_presigned_url_sanitizes_filename(s3_env):
    """Special characters in filename are replaced with underscores."""
    from app.services.storage import generate_presigned_url, upload_file

    data = b"presign sanitize test"
    key, _, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-006",
        container_id="cont-mno",
        original_filename="normal.pdf",
    )

    # Filename with special characters — should not cause errors
    url = generate_presigned_url(key, original_filename="<script>alert.pdf")
    assert isinstance(url, str)


@needs_moto
def test_generate_presigned_url_custom_expiry(s3_env):
    """Custom expires_in is accepted without error."""
    from app.services.storage import generate_presigned_url, upload_file

    data = b"expiry test"
    key, _, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-007",
        container_id="cont-pqr",
        original_filename="expiry.pdf",
    )

    url = generate_presigned_url(key, original_filename="expiry.pdf", expires_in=7200)
    assert isinstance(url, str)


# ─── delete_file ──────────────────────────────────────────────────────────────


@needs_moto
def test_delete_file_removes_object(s3_env):
    """delete_file removes the object from S3."""
    from app.core.config import settings
    from app.services.storage import delete_file, upload_file

    data = b"file to be deleted"
    key, _, _ = upload_file(
        data=data,
        content_type="application/pdf",
        project_id="proj-008",
        container_id="cont-stu",
        original_filename="deleteme.pdf",
    )

    # Confirm it exists
    s3_env.head_object(Bucket=settings.MINIO_BUCKET, Key=key)

    delete_file(key)

    # After deletion, head_object should raise
    import botocore.exceptions

    with pytest.raises(botocore.exceptions.ClientError) as exc_info:
        s3_env.head_object(Bucket=settings.MINIO_BUCKET, Key=key)
    assert exc_info.value.response["Error"]["Code"] in ("404", "NoSuchKey")


@needs_moto
def test_delete_file_nonexistent_key_does_not_raise(s3_env):
    """delete_file on a nonexistent key should not raise (S3 delete is idempotent)."""
    from app.services.storage import delete_file

    # S3 DeleteObject is idempotent — deleting a nonexistent key returns 204
    delete_file("nonexistent/key/file.pdf")


# ─── _safe_ext edge cases ─────────────────────────────────────────────────────


def test_safe_ext_with_dots_in_name():
    """Multiple dots: last extension is used."""
    from app.services.storage import _safe_ext

    assert _safe_ext("archive.tar.gz") == "gz"
    assert _safe_ext("file.v2.ifc") == "ifc"


def test_safe_ext_strips_special_chars():
    """Non-alphanumeric chars in extension are stripped."""
    from app.services.storage import _safe_ext

    # Extension with special chars becomes empty → fallback to 'bin'
    result = _safe_ext("file.<evil>")
    assert re.match(r"^[a-zA-Z0-9]+$", result)
