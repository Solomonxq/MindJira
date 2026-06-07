
from datetime import datetime
from pydantic import BaseModel
 
 
class Issue(BaseModel):
    id: str
    key: str
    summary: str
    description: str | None
    issue_type: str
    status: str
    epic_key: str | None
    sprint_id: int | None
    assignee: str | None
    created: datetime
    updated: datetime
 
    @classmethod
    def from_jira(cls, data: dict) -> "Issue":
        fields = data.get("fields", {})
 
        sprint_id = None
        sprints = fields.get("customfield_10020")
        if sprints and isinstance(sprints, list):
            sprint_id = sprints[-1].get("id")
 
        return cls(
            id=data["id"],
            key=data["key"],
            summary=fields.get("summary", ""),
            description=fields.get("description"),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            status=fields.get("status", {}).get("name", ""),
            epic_key=fields.get("customfield_10014"),
            sprint_id=sprint_id,
            assignee=fields.get("assignee", {}).get("emailAddress") if fields.get("assignee") else None,
            created=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
            updated=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
        )
