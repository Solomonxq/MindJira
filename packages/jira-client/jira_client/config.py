from pydantic_settings import BaseSettings, SettingsConfigDict
 
 
class JiraSettings(BaseSettings):
    JIRA_API_TOKEN: str
    JIRA_CACHE_TTL: int = 300
 
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JIRA_",
        extra="ignore"
    )
 
 
settings = JiraSettings()
 
