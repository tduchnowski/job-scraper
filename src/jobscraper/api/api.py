import aiohttp
from fastapi import FastAPI, Request
from sqlalchemy import select

from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.models import UserSubscriptionORM
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
    async with SessionLocal() as session:
        subs_query = select(UserSubscriptionORM)
        subs = await session.execute(subs_query)
        for sub in subs.scalars():
            print(sub.id, sub.user.username)
    return {"ok": True}
