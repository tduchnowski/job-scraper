import aiohttp
from fastapi import FastAPI, Request
from sqlalchemy import and_, select
from sqlalchemy.orm.strategy_options import selectinload

from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.models import JobORM, UserSubscriptionORM
from jobscraper.storage.repository import JobRepository
from jobscraper.storage.session import SessionLocal
from jobscraper.utils.logger import setup_logger
from loguru import logger

setup_logger()
app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    """
    Telegram bot updates
    """
    return {"ok": True}


@app.post("/scrape")
async def scrape_jobs():
    """
    Triggers scraping of job boards and updating DB with new jobs
    This endpoint is intended for scheduler use only. Not publicly available.
    """
    logger.info("Starting scheduled job scraping")
    try:
        async with aiohttp.ClientSession() as session:
            indeed = IndeedScraper(session)
            jobs = await indeed.scrape_job_list("python developer", "Polska")

        async with SessionLocal() as session:
            repo = JobRepository(session)
            for job in jobs:
                await repo.upsert(job)

        return {
            "ok": True,
            "jobs_scraped": len(jobs),
        }
    except aiohttp.ClientError as e:
        logger.error(f"Network error during scraping: {e}")
        return {"ok": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/dispatch")
async def dispatch_jobs():
    """
    Triggers sending new jobs to users
    """
    logger.info("Starting scheduled dispatcher")
    async with SessionLocal() as session:
        subs_query = select(UserSubscriptionORM).options(
            selectinload(UserSubscriptionORM.user)
        )
        subs = await session.execute(subs_query)
        for sub in subs.scalars():
            stmt = select(JobORM).where(
                and_(
                    JobORM.status == "NEW",
                    JobORM.location == sub.location,
                    JobORM.category == sub.category,
                    JobORM.created_at > sub.last_notified_at,
                )
            )
            matching_jobs = (await session.execute(stmt)).scalars().all()
            logger.info(f"Found {len(matching_jobs)} for user: {sub.user.username}")
            # for a matching job send the notification
    return {"ok": True}
