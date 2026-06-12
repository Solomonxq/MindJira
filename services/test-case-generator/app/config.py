import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "TEST_CASE_GENERATOR_")


class Settings(BaseSettings):
    PROJECT_NAME: str = "test-case-generator"
    ENV: str = "development"
    DEBUG: bool = True
    DB_URL: str
    REDIS_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore",
    )


settings = Settings()
