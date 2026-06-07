import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "SPRINT_")

class Settings(BaseSettings):
    PROJECT_NAME: str = "sprint-summary" 
    ENV: str = "development"
    DEBUG: bool = True
    REDIS_URL: str
    JIRA_API_TOKEN:str
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore"
    )

settings = Settings()