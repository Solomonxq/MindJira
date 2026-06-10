import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class JiraSettings(BaseSettings):
    JIRA_API_TOKEN: str | None = None
    JIRA_CACHE_TTL: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore"
    )


# Load settings and provide a fallback to prefixed env vars used by services
settings = JiraSettings()
if not settings.JIRA_API_TOKEN:
    # allow service-specific env var (e.g. SPRINT_JIRA_API_TOKEN) to satisfy package
    settings.JIRA_API_TOKEN = os.environ.get("SPRINT_JIRA_API_TOKEN") or os.environ.get("JIRA_API_TOKEN")
 
