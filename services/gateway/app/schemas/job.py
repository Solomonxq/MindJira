import uuid
from datetime import datetime
from pydantic import BaseModel
 
 
class JobRunRequest(BaseModel):
    service_name: str
    jql: str | None = None
    issue_keys: list[str] = []
 
 
class JiraWebhookPayload(BaseModel):
    webhookEvent: str
    issue: dict | None = None
 
 
class JobResponse(BaseModel):
    id: uuid.UUID
    service_name: str
    trigger_type: str
    jql: str | None
    issue_keys: list[str]
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime
 
    model_config = {"from_attributes": True}
 
