from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)


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
