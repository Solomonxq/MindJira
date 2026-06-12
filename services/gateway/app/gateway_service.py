import json
from uuid import UUID

import structlog
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.job import Job
from app.schemas.job import JobRunRequest

logger = structlog.get_logger()

QUEUE_NAME = "mindjira:jobs"


class JobService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self._session = session
        self._redis = redis

    async def create_job(
        self,
        service_name: str,
        trigger_type: str,
        jql: str | None = None,
        issue_keys: list[str] | None = None,
    ) -> Job:
        job = Job(
            service_name=service_name,
            trigger_type=trigger_type,
            jql=jql,
            issue_keys=issue_keys or [],
            status="pending",
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)

        await self._push_to_queue(job)
        logger.info("Job created", job_id=str(job.id), service=service_name, trigger=trigger_type)
        return job

    async def _push_to_queue(self, job: Job) -> None:
        payload = {
            "job_id": str(job.id),
            "service_name": job.service_name,
            "jql": job.jql,
            "issue_keys": job.issue_keys,
        }
        await self._redis.lpush(QUEUE_NAME, json.dumps(payload))
        logger.debug("Job pushed to queue", job_id=str(job.id))

    async def get_job(self, job_id: UUID) -> Job | None:
        result = await self._session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_history(self, limit: int = 50) -> list[Job]:
        result = await self._session.execute(
            select(Job).order_by(desc(Job.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        error: str | None = None,
    ) -> None:
        job = await self.get_job(job_id)
        if not job:
            return
        job.status = status
        if status == "running":
            job.started_at = datetime.now(timezone.utc)
        if status in ("done", "failed"):
            job.finished_at = datetime.now(timezone.utc)
        if error:
            job.error = error
        await self._session.commit()