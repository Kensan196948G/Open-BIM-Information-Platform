from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.organization import Organization
from app.models.user import UserOrganization

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    is_active: bool


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser,
    db: DB,
) -> list[OrganizationResponse]:
    if current_user.is_platform_admin:
        result = await db.execute(
            select(Organization)
            .where(Organization.is_active.is_(True))
            .order_by(Organization.name)
        )
        orgs = result.scalars().all()
    else:
        result = await db.execute(
            select(Organization)
            .join(UserOrganization, UserOrganization.organization_id == Organization.id)
            .where(
                UserOrganization.user_id == current_user.id,
                Organization.is_active == True,  # noqa: E712
            )
            .order_by(Organization.name)
        )
        orgs = result.scalars().all()

    return [OrganizationResponse.model_validate(o) for o in orgs]
