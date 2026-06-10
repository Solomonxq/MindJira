import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
 
import httpx
from redis.asyncio import Redis
 
from jira_client.config import settings
from jira_client.exceptions import (
    JiraAuthError,
    JiraNotFoundError,
    JiraRateLimitError,
    JiraServerError,
)
from jira_client.models import Issue
 
logger = structlog.get_logger()
 
DEFAULT_FIELDS = [
    "summary",
    "description",
    "issuetype",
    "status",
    "assignee",
    "customfield_10014",  
    "customfield_10020",  
    "created",
    "updated",
]
 
 
class JiraClient:
    def __init__(self, base_url: str, email: str, redis: Redis):
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._redis = redis
        self._http = httpx.AsyncClient(
            base_url=f"{self._base_url}/rest/api/3",
            auth=(email, settings.JIRA_API_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
        )
 
    async def close(self):
        await self._http.aclose()
 
    def _cache_key(self, *parts: str) -> str:
        return f"jira:{self._base_url}:" + ":".join(parts)
 
    async def _get_cached(self, key: str) -> dict | None:
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return None
 
    async def _set_cached(self, key: str, data: dict) -> None:
        await self._redis.setex(key, settings.JIRA_CACHE_TTL, json.dumps(data))
 
    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 401:
            raise JiraAuthError("Invalid credentials")
        if response.status_code == 403:
            raise JiraAuthError("Access denied")
        if response.status_code == 404:
            raise JiraNotFoundError("Resource not found")
        if response.status_code == 429:
            raise JiraRateLimitError("Rate limit exceeded")
        if response.status_code >= 500:
            raise JiraServerError(f"Jira server error: {response.status_code}")
        if response.status_code >= 400:
            # log response body for easier debugging of client errors (e.g. 410)
            try:
                body = response.text
            except Exception:
                body = "<unreadable response body>"
            logger.error("Jira API error", status_code=response.status_code, body=body)
        response.raise_for_status()
        return response.json()
 
    @retry(
        retry=retry_if_exception_type((JiraRateLimitError, JiraServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def search_issues(self, jql: str, fields: list[str] = DEFAULT_FIELDS) -> list[Issue]:
        cache_key = self._cache_key("search", jql, ",".join(fields))
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug("Jira search cache hit", jql=jql)
            return [Issue.from_jira(i) for i in cached]
 
        # Use the newer search JQL endpoint per Atlassian change (CHANGE-2046)
        # POST /rest/api/3/search/jql
        response = await self._http.post(
            "/search/jql",
            json={"jql": jql, "fields": fields, "maxResults": 100},
        )
        data = self._handle_response(response)
        issues_raw = data.get("issues", [])
        await self._set_cached(cache_key, issues_raw)
        logger.info("Jira search", jql=jql, count=len(issues_raw))
        return [Issue.from_jira(i) for i in issues_raw]
 
    @retry(
        retry=retry_if_exception_type((JiraRateLimitError, JiraServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_issue(self, issue_id: str) -> Issue:
        cache_key = self._cache_key("issue", issue_id)
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug("Jira get_issue cache hit", issue_id=issue_id)
            return Issue.from_jira(cached)
 
        response = await self._http.get(f"/issue/{issue_id}")
        data = self._handle_response(response)
        await self._set_cached(cache_key, data)
        return Issue.from_jira(data)
 
    async def edit_issue(self, issue_id: str, fields: dict) -> None:
        response = await self._http.put(
            f"/issue/{issue_id}",
            json={"fields": fields},
        )
        self._handle_response(response)
        await self._redis.delete(self._cache_key("issue", issue_id))
        logger.info("Jira issue edited", issue_id=issue_id)
 
    async def add_comment(self, issue_id: str, body: str) -> None:
        response = await self._http.post(
            f"/issue/{issue_id}/comment",
            json={"body": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": body}]}
            ]}},
        )
        self._handle_response(response)
        logger.info("Jira comment added", issue_id=issue_id)
 
    async def create_subtask(self, parent_id: str, summary: str, description: str) -> Issue:
        parent = await self.get_issue(parent_id)
        response = await self._http.post(
            "/issue",
            json={"fields": {
                "project": {"key": parent.key.split("-")[0]},
                "parent": {"id": parent_id},
                "summary": summary,
                "description": {"type": "doc", "version": 1, "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                ]},
                "issuetype": {"name": "Subtask"},
            }},
        )
        data = self._handle_response(response)
        return await self.get_issue(data["id"])
 
    async def get_epic_issues(self, epic_id: str) -> list[Issue]:
        return await self.search_issues(f'"Epic Link" = {epic_id} OR "Parent" = {epic_id}')
 
    async def get_sprint_issues(self, sprint_id: int) -> list[Issue]:
        return await self.search_issues(f"sprint = {sprint_id}")
 
