import re

from pydantic import BaseModel, Field, field_validator


class SegmentDefinitionSchema(BaseModel):
    key: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    required: bool = True
    max_length: int | None = Field(default=None, ge=1, le=500)
    min_length: int | None = Field(default=None, ge=1, le=500)
    allowed_values: list[str] = Field(default_factory=list, max_length=100)
    pattern: str | None = Field(default=None, max_length=200)
    description: str = Field(default="", max_length=500)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc
        return v


class NamingRuleCreate(BaseModel):
    separator: str = Field(default="-", min_length=1, max_length=5)
    segments: list[SegmentDefinitionSchema] = Field(min_length=1, max_length=20)


class NamingRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    separator: str
    segments: list[SegmentDefinitionSchema]
    is_default: bool = False
