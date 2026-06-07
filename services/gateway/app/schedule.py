import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger()

SCHEDULES = [
    {
        "name": "enrich_descriptions",
        "cron": "0 2 * * *",
        "service": "description-enricher",
        "jql": "description is EMPTY AND created >= -7d",
        "trigger_type": "cron",
    },
    {
        "name": "sprint_health_check",
        "cron": "0 9 * * 1",
        "service": "sprint-summary",
        "jql": "status changed to 'In Progress' before -14d AND status != Done",
        "trigger_type": "cron",
    },
    {
        "name": "generate_test_cases",
        "cron": "0 3 * * *",
        "service": "test-case-generator",
        "jql": "issuetype = Story AND status = 'Ready for QA'",
        "trigger_type": "cron",
    },
]


def create_scheduler(job_callback) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    for schedule in SCHEDULES:
        hour, minute = schedule["cron"].split()[1], schedule["cron"].split()[0]
        scheduler.add_job(
            job_callback,
            CronTrigger.from_crontab(schedule["cron"]),
            kwargs={
                "service_name": schedule["service"],
                "trigger_type": schedule["trigger_type"],
                "jql": schedule["jql"],
            },
            id=schedule["name"],
            name=schedule["name"],
            replace_existing=True,
        )
        logger.info("Scheduled job", name=schedule["name"], cron=schedule["cron"])

    return scheduler