from fastapi import APIRouter
from pydantic import BaseModel

from app.core.deps import CurrentUser
from app.services.naming_validator import validate_identifier

router = APIRouter(prefix="/naming", tags=["naming"])


class ValidateNameRequest(BaseModel):
    identifier: str
    project_id: str | None = None


class SegmentIssueResponse(BaseModel):
    segment_key: str
    segment_label: str
    value: str | None
    level: str
    message: str


class ValidateNameResponse(BaseModel):
    identifier: str
    level: str
    is_compliant: bool
    issues: list[SegmentIssueResponse]
    issues_text: str


@router.post("/validate", response_model=ValidateNameResponse)
async def validate_name(
    body: ValidateNameRequest,
    current_user: CurrentUser,
) -> ValidateNameResponse:
    result = validate_identifier(body.identifier)
    return ValidateNameResponse(
        identifier=result.identifier,
        level=result.level.value,
        is_compliant=result.is_compliant,
        issues=[
            SegmentIssueResponse(
                segment_key=i.segment_key,
                segment_label=i.segment_label,
                value=i.value,
                level=i.level.value,
                message=i.message,
            )
            for i in result.issues
        ],
        issues_text=result.issues_text,
    )
