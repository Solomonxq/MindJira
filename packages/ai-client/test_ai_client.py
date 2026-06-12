import asyncio
import os
from dotenv import load_dotenv

import structlog

from ai_client import AIClient
from ai_client.config import AIClientSettings

logger = structlog.get_logger()

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


async def main():
    config = AIClientSettings()
    api_key = os.getenv("AI_ANTHROPIC_API_KEY") or config.ANTHROPIC_API_KEY
    model = os.getenv("AI_ANTHROPIC_MODEL") or config.ANTHROPIC_MODEL
    base_url = os.getenv("AI_BASE_URL") or config.BASE_URL

    if not api_key:
        logger.error("AI_ANTHROPIC_API_KEY not found in environment")
        return

    client = AIClient(api_key=api_key, model=model, base_url=base_url)
    provider = "NVIDIA NIM (OpenAI-compatible)" if base_url else "Anthropic"
    logger.info("Starting AIClient test", provider=provider, model=model)

    try:
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt='Say exactly "Hello from MindJira AI" and nothing else.',
            max_tokens=50,
        )
        logger.info(
            "AIClient test passed",
            content=response.content.strip(),
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
    except Exception:
        logger.exception("AIClient test failed")


if __name__ == "__main__":
    asyncio.run(main())
