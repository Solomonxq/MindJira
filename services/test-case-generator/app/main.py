import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from ai_client.client import AIClient
from jira_client.client import JiraClient

from app.config import settings
from app.db import async_session_factory, engine
from app.models.base import Base
from app.schemas.test_case import GenerateRequest, GenerateResponse
from app import task

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(
        20 if not settings.DEBUG else 10
    ),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def _create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service initialization", service=settings.PROJECT_NAME, env=settings.ENV)
    await _create_tables()

    redis = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis

    if settings.JIRA_BASE_URL and settings.JIRA_EMAIL:
        app.state.jira = JiraClient(
            settings.JIRA_BASE_URL, settings.JIRA_EMAIL, redis
        )
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
    root_path="/test-case-generator",
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
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.post("/generate/{issue_key}", response_model=GenerateResponse, tags=["Test Cases"])
async def generate_single(issue_key: str, language: str | None = None):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    markdown = await task.generate_test_cases(
        app.state.jira, app.state.ai, issue_key, language=language
    )
    return GenerateResponse(issue_key=issue_key, test_cases_markdown=markdown)


@app.post("/generate", response_model=list[GenerateResponse], tags=["Test Cases"])
async def generate_batch(request: GenerateRequest):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    markdown = await task.generate_test_cases(
        app.state.jira,
        app.state.ai,
        request.issue_key,
        language=request.language,
    )
    return [GenerateResponse(issue_key=request.issue_key, test_cases_markdown=markdown)]
