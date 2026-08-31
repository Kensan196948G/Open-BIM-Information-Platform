import base64
import hashlib
import io

from app.services import demo_seed


class _Paginator:
    def __init__(self, pages: list[dict]) -> None:
        self.pages = pages
        self.calls: list[dict] = []

    def paginate(self, **kwargs):
        self.calls.append(kwargs)
        return self.pages


class _S3Client:
    def __init__(self, pages: list[dict] | None = None) -> None:
        self.put_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.paginator = _Paginator(pages or [])

    def put_object(self, **kwargs) -> None:
        self.put_calls.append(kwargs)

    def get_paginator(self, operation: str) -> _Paginator:
        assert operation == "list_objects_v2"
        return self.paginator

    def delete_object(self, **kwargs) -> None:
        self.delete_calls.append(kwargs)


def test_build_demo_pdf_is_valid_and_deterministic() -> None:
    first = demo_seed.build_demo_object("FUT-BR-2026", "DRAWING-001", is_ifc=False)
    second = demo_seed.build_demo_object("FUT-BR-2026", "DRAWING-001", is_ifc=False)

    assert first == second
    assert first.storage_key == "demo/FUT-BR-2026/DRAWING-001.pdf"
    assert first.data.startswith(b"%PDF-1.4")
    assert first.data.endswith(b"%%EOF\n")
    assert first.checksum_sha256 == hashlib.sha256(first.data).hexdigest()


def test_build_demo_ifc_contains_minimal_project() -> None:
    result = demo_seed.build_demo_object("MGM-2027", "MODEL-002", is_ifc=True)

    assert result.storage_key == "demo/MGM-2027/MODEL-002.ifc"
    assert result.data.startswith(b"ISO-10303-21;\n")
    assert b"FILE_SCHEMA(('IFC4'))" in result.data
    assert b"IFCPROJECT" in result.data
    assert result.data.endswith(b"END-ISO-10303-21;\n")


def test_upload_demo_object_sends_protocol_checksum(monkeypatch) -> None:
    client = _S3Client()
    monkeypatch.setattr(demo_seed.storage, "get_s3_client", lambda: client)
    result = demo_seed.build_demo_object("FUT-BR-2026", "DRAWING-001", is_ifc=False)

    demo_seed.upload_demo_object(result)

    call = client.put_calls[0]
    assert call["Bucket"] == demo_seed.settings.MINIO_BUCKET
    assert call["Key"] == result.storage_key
    assert isinstance(call["Body"], io.BytesIO)
    assert call["Body"].read() == result.data
    assert call["ContentLength"] == result.size_bytes
    assert call["ChecksumSHA256"] == base64.b64encode(
        bytes.fromhex(result.checksum_sha256)
    ).decode("ascii")
    assert call["Metadata"]["sha256"] == result.checksum_sha256


def test_prune_stale_demo_objects_is_prefix_scoped(monkeypatch) -> None:
    keep = "demo/FUT-BR-2026/keep.pdf"
    stale = "demo/FUT-BR-2026/stale.pdf"
    client = _S3Client(
        [
            {"Contents": [{"Key": keep}, {"Key": stale}]},
            {"Contents": [{"Key": "outside/not-deleted.ifc"}, {"Size": 1}]},
        ]
    )
    monkeypatch.setattr(demo_seed.storage, "get_s3_client", lambda: client)

    removed = demo_seed.prune_stale_demo_objects({keep})

    assert removed == (stale,)
    assert client.paginator.calls == [
        {"Bucket": demo_seed.settings.MINIO_BUCKET, "Prefix": "demo/"}
    ]
    assert client.delete_calls == [
        {"Bucket": demo_seed.settings.MINIO_BUCKET, "Key": stale}
    ]
