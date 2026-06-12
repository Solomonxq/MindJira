import os
from pydantic_settings import BaseSettings, SettingsConfigDict
 
ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "GATEWAY_")
 
 
class Settings(BaseSettings):
    PROJECT_NAME: str = "gateway"
    ENV: str = "development"
    DEBUG: bool = True
    DB_URL: str
    REDIS_URL: str
    INTERNAL_SERVICE_TOKEN: str | None = None
    AUTH_SERVICE_URL: str = "http://traefik/auth"
    SPRINT_SUMMARY_SERVICE_URL: str = "http://traefik/sprint-summary"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore",
    )
 
 
settings = Settings()
 
