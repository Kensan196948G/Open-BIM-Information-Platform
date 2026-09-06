from datetime import datetime

from pydantic import BaseModel

from app.models.container import ContainerState, ContainerType, SecurityLevel


class ContainerCreate(BaseModel):
    identifier: str
    title: str
    container_type: ContainerType = ContainerType.document
    security_level: SecurityLevel = SecurityLevel.limited
    current_revision: str = "P01"
    classification_id: str | None = None


class ContainerUpdate(BaseModel):
    title: str | None = None
    security_level: SecurityLevel | None = None
    classification_id: str | None = None


class ContainerResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    identifier: str
    title: str
    container_type: ContainerType
    current_state: ContainerState
    current_revision: str
    current_branch: str | None
    security_level: SecurityLevel
    naming_valid: bool
    naming_issues: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class StateTransitionRequest(BaseModel):
    action: str
    comment: str | None = None
    # Optional client-side expectation; if provided, server verifies it matches
    # the computed next state (defense against client/server divergence).
    target_state: ContainerState | None = None


class ContainerListResponse(BaseModel):
    items: list[ContainerResponse]
    total: int
    page: int
    size: int


# ─── Revision diff (Issue #52) ────────────────────────────────────────────────


class RevisionDiffFileMeta(BaseModel):
    """File metadata snapshot attached to a single revision (nullable if unset)."""

    id: str | None = None
    original_filename: str | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None


class RevisionDiffTextField(BaseModel):
    """Before/after comparison for a single text field."""

    field: str
    from_value: str | None
    to_value: str | None
    changed: bool
    diff_lines: list[str] = []


class RevisionDiffFileComparison(BaseModel):
    """File metadata comparison between the two revisions."""

    from_file: RevisionDiffFileMeta | None
    to_file: RevisionDiffFileMeta | None
    original_filename_changed: bool
    content_type_changed: bool
    file_size_bytes_changed: bool
    checksum_sha256_changed: bool
    identical: bool


class RevisionDiffSummary(BaseModel):
    """Metadata summary for one side of a revision diff."""

    id: str
    revision_code: str
    version_code: str | None
    change_reason: str | None
    change_summary: str | None
    created_by: str
    created_at: datetime
    file: RevisionDiffFileMeta | None


class RevisionDiffResponse(BaseModel):
    """Comparison result between two revisions of the same container."""

    container_id: str
    from_revision: RevisionDiffSummary
    to_revision: RevisionDiffSummary
    text_diffs: list[RevisionDiffTextField]
    file_diff: RevisionDiffFileComparison
