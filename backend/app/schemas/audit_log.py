from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    occurred_at: str
    event_type: str
    actor_id: str | None
    actor_ip: str | None
    target_type: str
    target_id: str | None
    operation: str
    result: str
    reason: str | None
    before_json: dict | None
    after_json: dict | None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    size: int
