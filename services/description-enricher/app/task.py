import asyncio
import json
import re

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ai_client.client import AIClient
from ai_client.exceptions import AIClientError
from jira_client.client import JiraClient
from jira_client.exceptions import JiraClientError
from jira_client.models import Issue

from app.config import settings
from app.models.enrichment import Enrichment

logger = structlog.get_logger()

QUEUE_NAME = "mindjira:jobs"


def _detect_language(text: str | None) -> str:
    """Detect Ukrainian vs English based on alphabet frequency."""
    if not text:
        return settings.DESCRIPTION_LANGUAGE
    cyrillic = len(re.findall(r"[а-яА-ЯіїєҐґ]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    return "uk" if cyrillic >= latin else "en"


def _build_system_prompt(language: str) -> str:
    if language == "uk":
        return (
            "Ти — технічний аналітик. Тобі дали Jira-тікет, і треба написати/доповнити опис українською мовою. "
            "Без води, тільки корисна інформація. "
            "Якщо не вистачає даних — вкажи [невідомо] замість домислів. "
            "Формат: Markdown, заголовки через ##. "
            "1. Якщо це Bug → напиши структуру: Контекст, Кроки відтворення, Очікуваний результат, Фактичний результат, Середовище. "
            "2. Якщо це Story / Task → напиши User Story формат (As a... I want... So that...) + Acceptance Criteria (Gherkin: Given/When/Then). "
            "3. Якщо опис вже є але короткий (< 50 слів) → розгорни його, зберігши суть. "
            "4. Враховуй контекст сусідніх тікетів, щоб опис був консистентним з епіком."
        )
    return (
        "You are a technical analyst. You are given a Jira ticket and must write/enrich its description in English. "
        "No fluff, only useful information. "
        "If data is missing, write [unknown] instead of guessing. "
        "Format: Markdown, headers with ##. "
        "1. If this is a Bug → write: Context, Steps to Reproduce, Expected Result, Actual Result, Environment. "
        "2. If this is a Story / Task → write User Story format (As a... I want... So that...) + Acceptance Criteria (Gherkin: Given/When/Then). "
        "3. If the description already exists but is short (< 50 words) → expand it while keeping the meaning. "
        "4. Consider neighboring tickets to keep the description consistent with the epic."
    )


def _build_user_prompt(
    issue: Issue,
    epic: Issue | None,
    related: list[Issue],
    language: str,
) -> str:
    lines = [
        f"Ticket type: {issue.issue_type or 'Task'}",
        f"Summary: {issue.summary}",
        f"Current description: {issue.description or '[missing]'}",
    ]
    if epic:
        lines.append(f"Epic: {epic.summary}")
    if related:
        lines.append("Related tickets in the same epic:")
        for r in related:
            lines.append(f"  - {r.key}: {r.summary} ({r.issue_type or 'unknown'})")
    lines.append(f"Language: {language}")
    return "\n".join(lines)


async def _fetch_context(
    jira: JiraClient, issue: Issue
) -> tuple[Issue | None, list[Issue]]:
    epic = None
    related = []
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


def markdown_to_adf(text: str) -> dict:
    """Convert plain Markdown text into a minimal Jira ADF document.

    Splits by double newlines into paragraphs. Code blocks and rich formatting
    are preserved as plain text paragraphs.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    content = []
    for paragraph in paragraphs:
        para_content = []
        for line in paragraph.split("\n"):
            if line.strip():
                para_content.append({"type": "text", "text": line + "\n"})
        if para_content:
            content.append({"type": "paragraph", "content": para_content})
    return {"type": "doc", "version": 1, "content": content}


async def apply_description(jira: JiraClient, issue_key: str, markdown: str) -> None:
    adf = markdown_to_adf(markdown)
    await jira.edit_issue(issue_key, {"description": adf})


async def enrich_issue(
    jira: JiraClient,
    ai: AIClient,
    session: AsyncSession,
    issue_key: str,
    language: str | None = None,
    apply_to_jira: bool | None = None,
) -> Enrichment:
    apply_to_jira = settings.AUTO_APPLY_TO_JIRA if apply_to_jira is None else apply_to_jira

    issue = await jira.get_issue(issue_key)
    detected_language = language or _detect_language(issue.description) or settings.DESCRIPTION_LANGUAGE

    epic, related = await _fetch_context(jira, issue)

    system = _build_system_prompt(detected_language)
    user = _build_user_prompt(issue, epic, related, detected_language)

    ai_resp = await ai.complete(
        system,
        user,
        max_tokens=2000,
        session=session,
        service_name=settings.PROJECT_NAME,
        issue_key=issue_key,
    )

    generated = ai_resp.content.strip()

    enrichment = Enrichment(
        issue_key=issue.key,
        issue_type=issue.issue_type,
        language=detected_language,
        original_description=issue.description,
        generated_description=generated,
        applied_to_jira=False,
    )

    if apply_to_jira:
        try:
            await apply_description(jira, issue.key, generated)
            enrichment.applied_to_jira = True
        except JiraClientError as exc:
            logger.error(
                "Failed to apply description to Jira",
                issue_key=issue_key,
                error=str(exc),
            )
            enrichment.error = str(exc)

    session.add(enrichment)
    await session.commit()
    await session.refresh(enrichment)
    return enrichment


async def process_job_payload(
    jira: JiraClient,
    ai: AIClient,
    session: AsyncSession,
    payload: dict,
) -> list[Enrichment]:
    issue_keys = payload.get("issue_keys") or []
    jql = payload.get("jql")

    if not issue_keys and jql:
        issues = await jira.search_issues(jql)
        issue_keys = [i.key for i in issues]

    logger.info("Processing enrichment job", issue_keys=issue_keys)
    results = []
    for key in issue_keys:
        try:
            enrichment = await enrich_issue(jira, ai, session, key)
            results.append(enrichment)
        except (AIClientError, JiraClientError) as exc:
            logger.error("Failed to enrich issue", issue_key=key, error=str(exc))
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
            if service_name != "description-enricher":
                # Not our job: push it back so the right service can pick it up.
                await redis.rpush(QUEUE_NAME, json.dumps(payload))
                await asyncio.sleep(0.5)
                continue

            async with session_factory() as session:
                await process_job_payload(jira, ai, session, payload)
        except Exception as exc:
            logger.error("Queue worker error", error=str(exc))
            await asyncio.sleep(1)
