from pydantic_settings import BaseSettings, SettingsConfigDict


class AIClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AI_",
        extra="ignore",
    )

    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.1
    BASE_URL: str | None = None
