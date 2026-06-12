import asyncio
import json

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from ai_client.client import AIClient
from ai_client.exceptions import AIClientError
from jira_client.client import JiraClient
from jira_client.exceptions import JiraClientError
from jira_client.models import Issue

from app.config import settings

logger = structlog.get_logger()

QUEUE_NAME = "mindjira:jobs"


def _detect_language(text: str | None) -> str:
    if not text:
        return settings.TEST_CASE_LANGUAGE
    cyrillic = sum(1 for ch in (text or "") if "\u0400" <= ch <= "\u04ff")
    latin = sum(1 for ch in (text or "") if ch.isascii() and ch.isalpha())
    return "uk" if cyrillic >= latin else "en"


def _build_system_prompt(language: str) -> str:
    if language == "uk":
        return (
            "Ти — QA-інженер з досвідом автоматизації. Тобі передали Jira-тікет, "
            "і треба згенерувати повний набір тест-кейсів українською мовою.\n\n"
            "Формат відповіді — Markdown з такими секціями:\n"
            "1. ## Аналіз функціоналу (3-5 пунктів)\n"
            "2. ## Позитивні тест-кейси (Happy Path) — таблиця | ID | Назва | Кроки | Очікуваний результат | Пріоритет |\n"
            "3. ## Негативні тест-кейси (Validation / Error Handling) — таблиця\n"
            "4. ## Edge Cases\n"
            "5. ## Інтеграційні тести (якщо актуально)\n"
            "6. ## Чеклист для ручного тестування\n\n"
            "Правила:\n"
            "- Кроки конкретні та відтворювані.\n"
            "- ID нумеруй TC-01, TC-02...\n"
            "- Пріоритет: High / Medium / Low.\n"
            "- Для API-тікетів додай приклади JSON request/response.\n"
            "- Якщо даних не вистачає — напиши [недостатньо даних] і опиши, що треба уточнити.\n"
            "- Не домислюй бізнес-логіку, якої немає в описі.\n\n"
            "Без води, тільки конкретика по тікету."
        )
    return (
        "You are a QA engineer with automation experience. You are given a Jira ticket "
        "and must generate a full set of test cases in English.\n\n"
        "Response format — Markdown with sections:\n"
        "1. ## Functional Analysis (3-5 bullet points)\n"
        "2. ## Positive Test Cases (Happy Path) — table | ID | Name | Steps | Expected Result | Priority |\n"
        "3. ## Negative Test Cases (Validation / Error Handling) — table\n"
        "4. ## Edge Cases\n"
        "5. ## Integration Tests (if applicable)\n"
        "6. ## Manual Testing Checklist\n\n"
        "Rules:\n"
        "- Steps must be concrete and reproducible.\n"
        "- Number IDs as TC-01, TC-02...\n"
        "- Priority: High / Medium / Low.\n"
        "- For API tickets include JSON request/response examples.\n"
        "- If data is missing write [insufficient data] and describe what to clarify.\n"
        "- Do not invent business logic not present in the description.\n\n"
        "No fluff, only ticket-specific details."
    )


def _build_user_prompt(issue: Issue, epic: Issue | None, language: str) -> str:
    lines = [
        f"Ticket key: {issue.key}",
        f"Type: {issue.issue_type or 'Task'}",
        f"Summary: {issue.summary}",
        f"Description: {issue.description or '[missing]'}",
        f"Status: {issue.status or '[unknown]'}",
    ]
    if epic:
        lines.append(f"Epic: {epic.summary}")
        lines.append(f"Epic description: {epic.description or '[missing]'}")
    lines.append(f"Language: {language}")
    return "\n".join(lines)


async def _fetch_context(
    jira: JiraClient, issue: Issue
) -> tuple[Issue | None, list[Issue]]:
    epic = None
    related: list[Issue] = []
    if not issue.epic_key:
        return epic, related

    try:
        epic = await jira.get_issue(issue.epic_key)
    except JiraClientError as exc:
        logger.warning("Failed to fetch epic", epic_key=issue.epic_key, error=str(exc))

    try:
        related = await jira.get_epic_issues(issue.epic_key)
        related = [r for r in related if r.key != issue.key]
    except JiraClientError as exc:
        logger.warning(
            "Failed to fetch epic issues", epic_key=issue.epic_key, error=str(exc)
        )

    return epic, related


async def generate_test_cases(
    jira: JiraClient,
    ai: AIClient,
    issue_key: str,
    language: str | None = None,
) -> str:
    issue = await jira.get_issue(issue_key)
    detected_language = language or _detect_language(issue.description)
    epic, _ = await _fetch_context(jira, issue)

    system = _build_system_prompt(detected_language)
    user = _build_user_prompt(issue, epic, detected_language)

    ai_resp = await ai.complete(
        system,
        user,
        max_tokens=3000,
        service_name=settings.PROJECT_NAME,
        issue_key=issue_key,
    )
    return ai_resp.content.strip()


async def process_job_payload(
    jira: JiraClient,
    ai: AIClient,
    payload: dict,
) -> list[dict]:
    issue_keys = payload.get("issue_keys") or []
    jql = payload.get("jql")

    if not issue_keys and jql:
        issues = await jira.search_issues(jql)
        issue_keys = [i.key for i in issues]

    logger.info("Processing test-case generation job", issue_keys=issue_keys)
    results = []
    for key in issue_keys:
        try:
            markdown = await generate_test_cases(jira, ai, key)
            results.append({"issue_key": key, "test_cases_markdown": markdown})
        except (AIClientError, JiraClientError) as exc:
            logger.error("Failed to generate test cases", issue_key=key, error=str(exc))
    return results


async def queue_worker(
    jira: JiraClient,
    ai: AIClient,
    redis: Redis,
    session_factory: async_sessionmaker,
) -> None:
    logger.info("Queue worker started", queue=QUEUE_NAME)
    while True:
        try:
            payload_raw = await redis.brpop(QUEUE_NAME, timeout=5)
            if not payload_raw:
                continue

            payload = json.loads(payload_raw[1])
            service_name = payload.get("service_name")
            if service_name != "test-case-generator":
                await redis.rpush(QUEUE_NAME, json.dumps(payload))
                await asyncio.sleep(0.5)
                continue

            async with session_factory() as session:
                await process_job_payload(jira, ai, payload)
        except Exception as exc:
            logger.error("Queue worker error", error=str(exc))
            await asyncio.sleep(1)
