import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "SPRINT_")

class Settings(BaseSettings):
    PROJECT_NAME: str = "sprint-summary" 
    ENV: str = "development"
    DEBUG: bool = True
    REDIS_URL: str
    JIRA_API_TOKEN:str
    JIRA_BASE_URL: str
    JIRA_EMAIL: str
    AI_API_KEY: str | None = None
    AI_MODEL: str | None = None
    AI_BASE_URL: str | None = None
    SLACK_WEBHOOK: str | None = None
    CONFLUENCE_API_URL: str | None = None
    CONFLUENCE_USER: str | None = None
    CONFLUENCE_TOKEN: str | None = None
    
    
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore"
    )

settings = Settings()