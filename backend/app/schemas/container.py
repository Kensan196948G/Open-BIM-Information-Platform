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


class StateTransitionRequest(BaseModel):
    action: str
    comment: str | None = None
    target_state: ContainerState


class ContainerListResponse(BaseModel):
    items: list[ContainerResponse]
    total: int
    page: int
    size: int
