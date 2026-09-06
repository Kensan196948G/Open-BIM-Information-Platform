"""Audit & compliance report response schemas (Issue #51).

Reports are computed on the fly from existing tables — no new persistence
model is introduced. See ``app.api.v1.reports`` for the aggregation logic.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ViolationType = Literal["naming_non_compliant", "rejected"]


class NamingViolationItem(BaseModel):
    container_id: str
    identifier: str
    title: str
    violation_type: ViolationType
    reason: str | None
    occurred_at: str | None
    current_state: str
    current_assignee_id: str | None


class NamingViolationsResponse(BaseModel):
    items: list[NamingViolationItem]
    total: int


class ApprovalDelayAssignee(BaseModel):
    assignee_id: str
    task_type: str
    status: str


class ApprovalDelayItem(BaseModel):
    workflow_id: str
    workflow_type: str
    target_type: str
    target_id: str
    container_identifier: str | None
    container_title: str | None
    created_at: datetime
    elapsed_hours: float
    assignees: list[ApprovalDelayAssignee]


class ApprovalDelaysResponse(BaseModel):
    items: list[ApprovalDelayItem]
    total: int
    threshold_hours: float


class RequirementsStatusItem(BaseModel):
    document_id: str
    doc_type: str
    title: str
    revision: str
    met_count: int
    partial_count: int
    not_met_count: int
    total_count: int
    fulfillment_rate: float


class RequirementsStatusResponse(BaseModel):
    items: list[RequirementsStatusItem]
    total: int
