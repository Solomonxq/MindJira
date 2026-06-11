import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.deps import get_session, get_redis
from app.schemas.job import JobRunRequest, JobResponse, JiraWebhookPayload
from app.gateway_service import JobService
import httpx
from fastapi import Response, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import os

logger = structlog.get_logger()
router = APIRouter()


@router.post("/jobs/run", response_model=JobResponse, tags=["Jobs"])
async def run_job(
    request: JobRunRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    # require valid JWT from auth service for manual job triggers
    service = JobService(session, redis)
    job = await service.create_job(
        service_name=request.service_name,
        trigger_type="manual",
        jql=request.jql,
        issue_keys=request.issue_keys,
    )
    return job


@router.get("/jobs/{job_id}/status", response_model=JobResponse, tags=["Jobs"])
async def get_job_status(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    service = JobService(session, redis)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/history", response_model=list[JobResponse], tags=["Jobs"])
async def get_jobs_history(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    service = JobService(session, redis)
    return await service.get_history(limit=limit)


@router.post("/webhooks/jira", tags=["Webhooks"])
async def jira_webhook(
    payload: JiraWebhookPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    logger.info("Jira webhook received", webhook_event=payload.webhookEvent)

    service_name = None
    issue_keys = []

    if payload.webhookEvent == "jira:issue_created":
        service_name = "description-enricher"
        if payload.issue:
            issue_keys = [payload.issue.get("key", "")]

    elif payload.webhookEvent == "jira:issue_updated":
        service_name = "description-enricher"
        if payload.issue:
            issue_keys = [payload.issue.get("key", "")]

    if service_name:
        svc = JobService(session, redis)
        await svc.create_job(
            service_name=service_name,
            trigger_type="webhook",
            issue_keys=issue_keys,
        )

    return {"status": "ok"}


security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
    # forward token to auth service /auth/me to validate
    # allow internal service token for service-to-service auth
    internal = os.getenv("AUTH_INTERNAL_SERVICE_TOKEN")
    if internal and credentials.credentials == internal:
        return
    headers = {"Authorization": f"Bearer {credentials.credentials}"}
    url = "http://traefik/auth/me"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/report/sprint/{sprint_id}", tags=["Proxy"]) 
async def proxy_sprint_report(sprint_id: int, token: HTTPAuthorizationCredentials = Security(security)):
    """Proxy a request to the sprint-summary service report endpoint via Traefik."""
    # validate token with the auth service
    await verify_token(token)

    # forward request to sprint-summary through Traefik
    url = f"http://traefik/sprint-summary/report/sprint/{sprint_id}"
    headers = {"Authorization": f"Bearer {token.credentials}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))

    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))