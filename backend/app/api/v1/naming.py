from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.naming_rule import ProjectNamingRule
from app.services.naming_validator import (
    NamingRule,
    SegmentDefinition,
    _default_iso19650_rule,
    validate_identifier,
)

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


async def _resolve_rule_for_project(
    project_id: str | None, db: AsyncSession
) -> NamingRule | None:
    if not project_id:
        return None
    db_result = await db.execute(
        select(ProjectNamingRule).where(ProjectNamingRule.project_id == project_id)
    )
    db_rule = db_result.scalar_one_or_none()
    if not db_rule:
        return _default_iso19650_rule(project_id)
    return NamingRule(
        project_id=project_id,
        separator=db_rule.separator,
        segments=[
            SegmentDefinition(
                key=s["key"],
                label=s.get("label", s["key"]),
                required=s.get("required", True),
                max_length=s.get("max_length"),
                min_length=s.get("min_length"),
                allowed_values=s.get("allowed_values", []),
                pattern=s.get("pattern"),
                description=s.get("description", ""),
            )
            for s in db_rule.segments
        ],
    )


@router.post("/validate", response_model=ValidateNameResponse)
async def validate_name(
    body: ValidateNameRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ValidateNameResponse:
    rule = await _resolve_rule_for_project(body.project_id, db)
    result = validate_identifier(body.identifier, rule)
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
