from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    email: str
    username: str
    full_name: str
    is_active: bool
    is_platform_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
