from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
 
 
class JobRunRequest(BaseModel):
    service_name: str
    jql: str | None = None
    issue_keys: list[str] = Field(default_factory=list)
 
 
class JiraWebhookPayload(BaseModel):
    webhookEvent: str
    issue: dict | None = None
 
 
class JobResponse(BaseModel):
    id: UUID
    service_name: str
    trigger_type: str
    jql: str | None
    issue_keys: list[str]
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime
 
    model_config = ConfigDict(from_attributes=True)
 
