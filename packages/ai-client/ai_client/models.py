from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float = Field(..., ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
