
from datetime import datetime
from pydantic import BaseModel, field_validator


def _adf_to_text(node) -> str:
    """Convert a Jira ADF (Atlassian Document Format) node to plain text.

    This function walks the ADF structure and concatenates all `text` nodes,
    inserting newlines after paragraphs for readability.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_adf_to_text(n) for n in node)
    if isinstance(node, dict):
        # direct text node
        if "text" in node:
            return str(node["text"])
        parts = []
        for child in node.get("content", []) or []:
            parts.append(_adf_to_text(child))
            if isinstance(child, dict) and child.get("type") == "paragraph":
                parts.append("\n")
        return "".join(parts)
    return ""


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
 
    @field_validator("description", mode="before")
    @classmethod
    def _validate_description(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, (dict, list)):
            text = _adf_to_text(v)
            return text.strip() if text else None
        return str(v)

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
