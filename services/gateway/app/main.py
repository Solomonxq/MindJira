
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.deps import get_redis_instance
from app.schedule import create_scheduler
 
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
scheduler = None
 
 
async def run_scheduled_job(service_name: str, trigger_type: str, jql: str):
    from app.db import async_session_factory
    from app.gateway_service import JobService
 
    redis = get_redis_instance()
    async with async_session_factory() as session:
        svc = JobService(session, redis)
        await svc.create_job(
            service_name=service_name,
            trigger_type=trigger_type,
            jql=jql,
        )
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    logger.info("Service initialization", service=settings.PROJECT_NAME, env=settings.ENV)
 
    scheduler = create_scheduler(run_scheduled_job)
    scheduler.start()
    logger.info("Scheduler started")
 
    yield
 
    scheduler.shutdown()
    logger.info("Scheduler stopped")
 
    redis = get_redis_instance()
    await redis.aclose()
 
 
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs",
    lifespan=lifespan,
    root_path="/gateway"
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
from app.api.router import router
app.include_router(router)
 
 
@app.get("/health", tags=["Infrastructure"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
