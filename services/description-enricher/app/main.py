import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from ai_client.client import AIClient
from jira_client.client import JiraClient

from app.config import settings
from app.db import async_session_factory, engine
from ai_client.db import Base as AIBase

from app.models.enrichment import Base
from app.schemas.enrichment import EnrichRequest, EnrichResponse
from app import task

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(20 if not settings.DEBUG else 10),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def _create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(AIBase.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service initialization", service=settings.PROJECT_NAME, env=settings.ENV)
    await _create_tables()

    redis = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis

    if settings.JIRA_BASE_URL and settings.JIRA_EMAIL:
        app.state.jira = JiraClient(settings.JIRA_BASE_URL, settings.JIRA_EMAIL, redis)
    else:
        app.state.jira = None

    if settings.AI_API_KEY and settings.AI_MODEL:
        logger.info("AI client config", model=settings.AI_MODEL, base_url=settings.AI_BASE_URL)
        app.state.ai = AIClient(
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
            base_url=settings.AI_BASE_URL,
        )
    else:
        app.state.ai = None

    worker_task = None
    if app.state.jira and app.state.ai:
        worker_task = asyncio.create_task(
            task.queue_worker(app.state.jira, app.state.ai, redis, async_session_factory)
        )

    try:
        yield
    finally:
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        if app.state.jira:
            await app.state.jira.close()
        if hasattr(app.state, "redis"):
            await app.state.redis.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
    lifespan=lifespan,
    root_path="/description-enricher",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Infrastructure"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }


@app.post("/enrich/{issue_key}", response_model=EnrichResponse, tags=["Enrichment"])
async def enrich_single(
    issue_key: str,
    language: str | None = None,
    apply_to_jira: bool | None = None,
):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    async with async_session_factory() as session:
        result = await task.enrich_issue(
            app.state.jira,
            app.state.ai,
            session,
            issue_key,
            language=language,
            apply_to_jira=apply_to_jira,
        )
        return result


@app.post("/enrich", response_model=list[EnrichResponse], tags=["Enrichment"])
async def enrich_batch(request: EnrichRequest):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    results = []
    async with async_session_factory() as session:
        for key in request.issue_keys:
            result = await task.enrich_issue(
                app.state.jira,
                app.state.ai,
                session,
                key,
                language=request.language,
                apply_to_jira=request.apply_to_jira,
            )
            results.append(result)
    return results
