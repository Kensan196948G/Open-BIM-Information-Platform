from pydantic import BaseModel, ConfigDict


class PermissionCreate(BaseModel):
    code: str
    description: str | None = None
    category: str


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    description: str | None
    category: str


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    name: str
    description: str | None
    is_system_role: bool


class RolePermissionAssign(BaseModel):
    permission_id: str


class RoleWithPermissionsResponse(RoleResponse):
    permissions: list[PermissionResponse] = []
