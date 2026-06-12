from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Literal

import anthropic
import openai
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ai_client.db import AILog
from ai_client.exceptions import AIAuthError, AIRateLimitError, AIResponseError
from ai_client.models import AIResponse


def _is_retryable_error(exc: BaseException) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        return status_code == 429 or status_code >= 500
    return False


class AIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_concurrent: int = 5,
        base_url: str | None = None,
    ) -> None:
        self._model = model
        self._semaphore = asyncio.Semaphore(max_concurrent)

        if base_url is not None:
            self._provider_type: Literal["anthropic", "openai"] = "openai"
            self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self._provider_type = "anthropic"
            self._client = anthropic.AsyncAnthropic(api_key=api_key)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Claude 3.5 Sonnet: $3 / 1M input, $15 / 1M output.
        # OpenAI-compatible providers (e.g. NVIDIA NIM) are estimated at half
        # of the Anthropic rate as a conservative default.
        if self._provider_type == "openai":
            return (input_tokens * 1.5 / 1_000_000) + (output_tokens * 7.5 / 1_000_000)
        return (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
        retry=retry_if_exception(_is_retryable_error),
        reraise=True,
    )
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        *,
        session: AsyncSession | None = None,
        service_name: str | None = None,
        issue_key: str | None = None,
    ) -> AIResponse:
        max_tokens = max_tokens or 4096

        async with self._semaphore:
            try:
                if self._provider_type == "anthropic":
                    response = await self._client.messages.create(
                        model=self._model,
                        max_tokens=max_tokens,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        temperature=0.1,
                    )
                    content = response.content[0].text
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                else:
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=0.1,
                    )
                    content = response.choices[0].message.content or ""
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code == 401:
                    raise AIAuthError(f"Authentication failed: {exc}") from exc
                if status_code == 429:
                    raise AIRateLimitError(f"Rate limit exceeded: {exc}") from exc
                if status_code is not None and status_code >= 500:
                    raise AIResponseError(f"API error {status_code}: {exc}") from exc
                raise AIResponseError(f"Unexpected error: {exc}") from exc

        cost = self._calculate_cost(input_tokens, output_tokens)

        ai_response = AIResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._model,
            cost_usd=cost,
            created_at=datetime.now(timezone.utc),
        )

        if session is not None:
            await self.log_usage(session, service_name, issue_key, ai_response)

        return ai_response

    async def complete_with_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int | None = None,
        *,
        session: AsyncSession | None = None,
        service_name: str | None = None,
        issue_key: str | None = None,
    ) -> dict:
        schema_text = json.dumps(schema, indent=2)
        enhanced_prompt = (
            f"{system_prompt}\n\n"
            f"You must respond with valid JSON only. "
            f"No markdown formatting, no explanations. "
            f"Match this schema:\n{schema_text}"
        )

        response = await self.complete(
            enhanced_prompt,
            user_prompt,
            max_tokens,
            session=session,
            service_name=service_name,
            issue_key=issue_key,
        )

        # Clean up possible markdown wrappers
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        return json.loads(cleaned)

    async def log_usage(
        self,
        session: AsyncSession,
        service_name: str | None,
        issue_key: str | None,
        response: AIResponse,
    ) -> None:
        log_entry = AILog(
            service_name=service_name or "unknown",
            issue_key=issue_key,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            model=response.model,
        )
        session.add(log_entry)
        await session.commit()
