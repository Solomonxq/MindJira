import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = os.getenv("SERVICE_ENV_PREFIX", "Deskrip")

class Settings(BaseSettings):
    PROJECT_NAME: str = "auth" 
    ENV: str = "development"
    DEBUG: bool = True
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        extra="ignore"
    )

settings = Settings()