import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "TEST_CASE_GENERATOR_")


class Settings(BaseSettings):
    PROJECT_NAME: str = "test-case-generator"
    ENV: str = "development"
    DEBUG: bool = True
    DB_URL: str
    REDIS_URL: str
    JIRA_API_TOKEN: str
    JIRA_BASE_URL: str
    JIRA_EMAIL: str
    AI_API_KEY: str
    AI_MODEL: str
    AI_BASE_URL: str | None = None
    TEST_CASE_LANGUAGE: str = "uk"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore",
    )


settings = Settings()
