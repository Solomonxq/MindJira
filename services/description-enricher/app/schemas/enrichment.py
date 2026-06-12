from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EnrichRequest(BaseModel):
    issue_keys: list[str] = Field(default_factory=list)
    language: str | None = None
    apply_to_jira: bool | None = None


class EnrichResponse(BaseModel):
    id: UUID
    issue_key: str
    issue_type: str | None
    language: str
    generated_description: str
    applied_to_jira: bool
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
