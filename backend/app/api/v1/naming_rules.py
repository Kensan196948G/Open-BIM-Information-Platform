from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.naming_rule import ProjectNamingRule
from app.models.project import Project
from app.models.user import UserOrganization
from app.schemas.naming_rule import NamingRuleCreate, NamingRuleResponse
from app.services.audit import record_audit
from app.services.naming_validator import (
    NamingRule,
    SegmentDefinition,
    _default_iso19650_rule,
)
from app.services.rbac import P_NAMING_RULE_MANAGE, require_permission

router = APIRouter(prefix="/projects/{project_id}/naming-rules", tags=["naming-rules"])


async def _get_project_or_404(project_id: str, current_user, db) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if not current_user.is_platform_admin:
        mem = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == project.organization_id,
            )
        )
        if not mem.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
    return project


def _db_rule_to_naming_rule(rule: ProjectNamingRule) -> NamingRule:
    """Convert DB model to the validator's NamingRule dataclass."""
    return NamingRule(
        project_id=rule.project_id,
        separator=rule.separator,
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
            for s in rule.segments
        ],
    )


def _default_rule_response(project_id: str) -> NamingRuleResponse:
    default = _default_iso19650_rule(project_id)
    from app.schemas.naming_rule import SegmentDefinitionSchema

    return NamingRuleResponse(
        id="default",
        project_id=project_id,
        separator=default.separator,
        segments=[
            SegmentDefinitionSchema(
                key=s.key,
                label=s.label,
                required=s.required,
                max_length=s.max_length,
                min_length=s.min_length,
                allowed_values=s.allowed_values,
                pattern=s.pattern,
                description=s.description,
            )
            for s in default.segments
        ],
        is_default=True,
    )


@router.get("", response_model=NamingRuleResponse)
async def get_naming_rule(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
) -> NamingRuleResponse:
    await _get_project_or_404(project_id, current_user, db)
    result = await db.execute(
        select(ProjectNamingRule).where(ProjectNamingRule.project_id == project_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return _default_rule_response(project_id)
    from app.schemas.naming_rule import SegmentDefinitionSchema

    return NamingRuleResponse(
        id=rule.id,
        project_id=rule.project_id,
        separator=rule.separator,
        segments=[SegmentDefinitionSchema(**s) for s in rule.segments],
        is_default=False,
    )


@router.put("", response_model=NamingRuleResponse, status_code=status.HTTP_200_OK)
async def upsert_naming_rule(
    request: Request,
    project_id: str,
    body: NamingRuleCreate,
    current_user: CurrentUser,
    db: DB,
) -> NamingRuleResponse:
    project = await _get_project_or_404(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_NAMING_RULE_MANAGE,
    )
    result = await db.execute(
        select(ProjectNamingRule).where(ProjectNamingRule.project_id == project_id)
    )
    rule = result.scalar_one_or_none()
    segments_data = [s.model_dump() for s in body.segments]
    if rule:
        rule.separator = body.separator
        rule.segments = segments_data
    else:
        rule = ProjectNamingRule(
            project_id=project_id,
            separator=body.separator,
            segments=segments_data,
        )
        db.add(rule)
    await db.flush()
    record_audit(
        db,
        event_type="naming_rule.upserted",
        operation="upsert",
        target_type="project",
        target_id=project_id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        after_json={
            "separator": rule.separator,
            "segment_count": len(rule.segments),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(rule)
    from app.schemas.naming_rule import SegmentDefinitionSchema

    return NamingRuleResponse(
        id=rule.id,
        project_id=rule.project_id,
        separator=rule.separator,
        segments=[SegmentDefinitionSchema(**s) for s in rule.segments],
        is_default=False,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_naming_rule(
    request: Request,
    project_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    project = await _get_project_or_404(project_id, current_user, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_NAMING_RULE_MANAGE,
    )
    result = await db.execute(
        select(ProjectNamingRule).where(ProjectNamingRule.project_id == project_id)
    )
    rule = result.scalar_one_or_none()
    if rule:
        await db.delete(rule)
        record_audit(
            db,
            event_type="naming_rule.deleted",
            operation="delete",
            target_type="project",
            target_id=project_id,
            actor_id=current_user.id,
            actor_ip=request.client.host if request.client else None,
            result="success",
        )
        await db.commit()
