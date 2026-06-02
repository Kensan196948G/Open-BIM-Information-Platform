from pydantic import BaseModel, Field


class SegmentDefinitionSchema(BaseModel):
    key: str
    label: str
    required: bool = True
    max_length: int | None = None
    min_length: int | None = None
    allowed_values: list[str] = Field(default_factory=list)
    pattern: str | None = None
    description: str = ""


class NamingRuleCreate(BaseModel):
    separator: str = "-"
    segments: list[SegmentDefinitionSchema]


class NamingRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    separator: str
    segments: list[SegmentDefinitionSchema]
    is_default: bool = False
