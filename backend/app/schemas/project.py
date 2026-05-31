from datetime import date

from pydantic import BaseModel

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    applied_standard: str = "ISO 19650"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    end_date: date | None = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    organization_id: str
    name: str
    code: str
    description: str | None
    status: ProjectStatus
    start_date: date | None
    end_date: date | None
    applied_standard: str


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
