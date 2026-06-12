import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from jira_client.client import JiraClient
from ai_client.client import AIClient
from app import task
 
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(20 if not settings.DEBUG else 10),
    cache_logger_on_first_use=True,
)
 
logger = structlog.get_logger()
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service initialization", service=settings.PROJECT_NAME, env=settings.ENV)

    # initialize Redis, Jira client and AI client
    redis = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis

    if settings.JIRA_BASE_URL and settings.JIRA_EMAIL:
        app.state.jira = JiraClient(settings.JIRA_BASE_URL, settings.JIRA_EMAIL, redis)
    else:
        app.state.jira = None

    if settings.AI_API_KEY and settings.AI_MODEL:
        logger.info("AI client config", model=settings.AI_MODEL, base_url=settings.AI_BASE_URL)
        app.state.ai = AIClient(api_key=settings.AI_API_KEY, model=settings.AI_MODEL, base_url=settings.AI_BASE_URL)
    else:
        app.state.ai = None

    try:
        yield
    finally:
        if app.state.jira:
            await app.state.jira.close()
        if hasattr(app.state, "redis"):
            await app.state.redis.close()
 
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
    lifespan=lifespan,
    root_path="/sprint-summary"
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
        "service": settings.PROJECT_NAME
    }


@app.post("/report/sprint/{sprint_id}", tags=["Reports"])
async def sprint_report(sprint_id: int):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    md = await task.generate_sprint_summary(app.state.jira, app.state.ai, sprint_id)

    # send to slack if configured
    if settings.SLACK_WEBHOOK:
        await task.send_to_slack(md)

    return {"report": md}


@app.post("/report/health", tags=["Reports"])
async def health_report(days: int = 14, send_slack: bool = True, save_confluence: bool = False):
    if not app.state.jira:
        raise HTTPException(status_code=500, detail="Jira client not configured")
    if not app.state.ai:
        raise HTTPException(status_code=500, detail="AI client not configured")

    md = await task.run_health_check(app.state.jira, app.state.ai, days=days)

    if send_slack and settings.SLACK_WEBHOOK:
        await task.send_to_slack(md)

    page_id = None
    if save_confluence:
        page_id = await task.save_to_confluence(f"Health check - {settings.PROJECT_NAME}", md)

    return {"report": md, "confluence_id": page_id}
