import asyncio
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from ai_client import AIClient


async def main():
    api_key = os.getenv("AI_ANTHROPIC_API_KEY")
    model = os.getenv("AI_ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    base_url = os.getenv("AI_BASE_URL")

    if not api_key:
        print("ERROR: AI_ANTHROPIC_API_KEY not found in environment")
        return

    client = AIClient(api_key=api_key, model=model, base_url=base_url)
    provider = "NVIDIA NIM (OpenAI-compatible)" if base_url else "Anthropic"
    print(f"Testing with provider: {provider}")
    print(f"Model: {model}")

    try:
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt='Say exactly "Hello from MindJira AI" and nothing else.',
            max_tokens=50,
        )
        print("\nAIClient test passed")
        print(f"   Content: {response.content.strip()}")
        print(f"   Model: {response.model}")
        print(f"   Input tokens: {response.input_tokens}")
        print(f"   Output tokens: {response.output_tokens}")
        print(f"   Cost USD: ${response.cost_usd:.6f}")
    except Exception as e:
        print(f"\nAIClient test failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
