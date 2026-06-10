import json
from typing import Optional

import httpx

from jira_client.client import JiraClient
from ai_client.client import AIClient
from app.config import settings


async def _serialize_issues(issues) -> str:
	lines = []
	for i in issues:
		desc = (i.description or "").replace("\n", " ")
		lines.append(f"- {i.key}: {i.summary} | assignee: {i.assignee or 'none'} | status: {i.status} | desc: {desc}")
	return "\n".join(lines)


async def generate_sprint_summary(jira: JiraClient, ai: AIClient, sprint_id: int) -> str:
	jql = f"sprint = {sprint_id} AND status = Done"
	issues = await jira.search_issues(jql)

	issues_text = await _serialize_issues(issues)

	system = (
		"You are an assistant that generates sprint summary reports in Ukrainian. "
		"Produce a Markdown report with sections: title, ✅ Зроблено, ⚠️ Перенесено, 🔴 Ризики, Changelog."
	)

	user = (
		f"Generate a Sprint summary for sprint {sprint_id}.\n\n"
		"Input: list of closed issues (Done).\n\n"
		"Issues:\n"
		f"{issues_text}\n\n"
		"Output must be a Markdown report and include a short changelog list."
	)

	ai_resp = await ai.complete(system, user, max_tokens=2000, service_name=settings.PROJECT_NAME)
	return ai_resp.content


async def run_health_check(jira: JiraClient, ai: AIClient, days: int = 14) -> str:
	jql = f'status changed to "In Progress" before -{days}d AND status != Done'
	issues = await jira.search_issues(jql)

	issues_text = await _serialize_issues(issues)

	system = (
		"You are an assistant that analyzes stuck Jira issues and provides recommendations in Ukrainian. "
		"Produce a Markdown report with sections: що буксує, можливі причини, рекомендації."
	)

	user = (
		f"Analyze the following issues that have been In Progress for more than {days} days.\n\n"
		"Issues:\n"
		f"{issues_text}\n\n"
		"For each issue, give likely reasons and recommended next steps. Also include a short summary at top."
	)

	ai_resp = await ai.complete(system, user, max_tokens=2000, service_name=settings.PROJECT_NAME)
	return ai_resp.content


async def send_to_slack(text: str, webhook: Optional[str] = None) -> None:
	webhook = webhook or settings.SLACK_WEBHOOK
	if not webhook:
		return
	async with httpx.AsyncClient() as client:
		await client.post(webhook, json={"text": text})


async def save_to_confluence(title: str, markdown: str) -> Optional[str]:
	if not settings.CONFLUENCE_API_URL or not settings.CONFLUENCE_USER or not settings.CONFLUENCE_TOKEN:
		return None
	url = settings.CONFLUENCE_API_URL.rstrip("/") + "/rest/api/content"
	auth = (settings.CONFLUENCE_USER, settings.CONFLUENCE_TOKEN)
	payload = {
		"type": "page",
		"title": title,
		"space": {"key": "~"},
		"body": {"storage": {"value": markdown, "representation": "storage"}},
	}
	async with httpx.AsyncClient() as client:
		r = await client.post(url, auth=auth, json=payload)
	if r.status_code in (200, 201):
		data = r.json()
		return data.get("id")
	return None

