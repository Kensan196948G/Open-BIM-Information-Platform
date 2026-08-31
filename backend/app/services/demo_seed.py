"""Deterministic object payloads used by the fictional MVP seed."""

import base64
import hashlib
import io
from dataclasses import dataclass

from app.core.config import settings
from app.services import storage

DEMO_OBJECT_PREFIX = "demo/"


@dataclass(frozen=True)
class DemoObject:
    storage_key: str
    original_filename: str
    content_type: str
    data: bytes
    checksum_sha256: str

    @property
    def size_bytes(self) -> int:
        return len(self.data)


def _minimal_pdf(identifier: str) -> bytes:
    text = f"Open BIM fictional demo file: {identifier}"
    stream = f"BT\n/F1 12 Tf\n72 720 Td\n({text}) Tj\nET\n".encode("ascii")
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
        + stream
        + b"endstream",
    )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for number, payload in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(payload)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _minimal_ifc(identifier: str) -> bytes:
    return (
        "ISO-10303-21;\n"
        "HEADER;\n"
        "FILE_DESCRIPTION(('ViewDefinition [ReferenceView_V1.2]'),'2;1');\n"
        f"FILE_NAME('{identifier}.ifc','2026-08-31T00:00:00',"
        "('Open BIM Demo'),('Open BIM Platform'),'seed_mvp.py',"
        "'Open BIM Platform','');\n"
        "FILE_SCHEMA(('IFC4'));\n"
        "ENDSEC;\n"
        "DATA;\n"
        "#1=IFCPERSON($,$,'Open BIM Demo',$,$,$,$,$);\n"
        "#2=IFCORGANIZATION($,'Open BIM Platform',$,$,$);\n"
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);\n"
        "#4=IFCAPPLICATION(#2,'0.1','Open BIM Platform','OPENBIM');\n"
        "#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,0);\n"
        "#6=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
        "#7=IFCUNITASSIGNMENT((#6));\n"
        "#8=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,$,$);\n"
        f"#9=IFCPROJECT('0YvctVUKr0kugbFTf53O9L',#5,'{identifier}',"
        "$,$,$,$,(#8),#7);\n"
        "ENDSEC;\n"
        "END-ISO-10303-21;\n"
    ).encode("ascii")


def build_demo_object(
    project_code: str, identifier: str, *, is_ifc: bool
) -> DemoObject:
    extension = "ifc" if is_ifc else "pdf"
    filename = f"{identifier}.{extension}"
    data = _minimal_ifc(identifier) if is_ifc else _minimal_pdf(identifier)
    return DemoObject(
        storage_key=f"{DEMO_OBJECT_PREFIX}{project_code}/{filename}",
        original_filename=filename,
        content_type="application/octet-stream" if is_ifc else "application/pdf",
        data=data,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
    )


def upload_demo_object(demo_object: DemoObject) -> None:
    storage.get_s3_client().put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=demo_object.storage_key,
        Body=io.BytesIO(demo_object.data),
        ContentType=demo_object.content_type,
        ContentLength=demo_object.size_bytes,
        ChecksumSHA256=base64.b64encode(
            bytes.fromhex(demo_object.checksum_sha256)
        ).decode("ascii"),
        Metadata={
            "original-filename": demo_object.original_filename,
            "sha256": demo_object.checksum_sha256,
            "seed-owner": "scripts/seed_mvp.py",
        },
    )


def prune_stale_demo_objects(expected_keys: set[str]) -> tuple[str, ...]:
    """Remove only seed-owned objects that are no longer in the current seed."""
    client = storage.get_s3_client()
    stale: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=settings.MINIO_BUCKET, Prefix=DEMO_OBJECT_PREFIX
    ):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if (
                isinstance(key, str)
                and key.startswith(DEMO_OBJECT_PREFIX)
                and key not in expected_keys
            ):
                stale.append(key)

    for key in sorted(stale):
        client.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
    return tuple(sorted(stale))
