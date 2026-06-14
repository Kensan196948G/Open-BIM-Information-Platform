from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentTypeValues = Literal[
    "OIR",
    "AIR",
    "PIR",
    "EIR",
    "BEP",
    "MIDP",
    "TIDP",
    "InformationProtocol",
    "Supplementary",
]
DocumentStatusValues = Literal[
    "draft", "under_review", "approved", "superseded", "withdrawn"
]


class RequirementItemCreate(BaseModel):
    item_no: str
    what: str
    when_required: str | None = None
    how_required: str | None = None
    for_whom: str | None = None
    acceptance_criteria: str | None = None
    responsible_user_id: str | None = None


class RequirementItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    item_no: str
    what: str
    when_required: str | None
    how_required: str | None
    for_whom: str | None
    acceptance_criteria: str | None
    responsible_user_id: str | None


class RequirementsDocumentCreate(BaseModel):
    doc_type: DocumentTypeValues
    title: str
    revision: str = "01"
    status: DocumentStatusValues = "draft"
    effective_from: str | None = None
    effective_to: str | None = None
    description: str | None = None


class RequirementsDocumentUpdate(BaseModel):
    title: str | None = None
    revision: str | None = None
    status: DocumentStatusValues | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    description: str | None = None


class RequirementsDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    owner_user_id: str | None
    doc_type: str
    title: str
    revision: str
    status: str
    effective_from: str | None
    effective_to: str | None
    description: str | None


class RequirementsDocumentListResponse(BaseModel):
    items: list[RequirementsDocumentResponse]
    total: int
