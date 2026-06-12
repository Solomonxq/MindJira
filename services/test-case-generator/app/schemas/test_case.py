from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    issue_key: str = Field(..., min_length=1)
    language: str | None = None


class GenerateResponse(BaseModel):
    issue_key: str
    test_cases_markdown: str

    model_config = ConfigDict(from_attributes=True)
