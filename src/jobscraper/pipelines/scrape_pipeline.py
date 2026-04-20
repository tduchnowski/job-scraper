from collections import defaultdict
from dataclasses import dataclass
import time
import random
import asyncio
from typing import Optional
import aiohttp
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jobscraper.config.scraping_config import SEARCH_QUERIES
from jobscraper.models.job import Job, JobCategory, JobLocation, JobStatus
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.services.notification_service import NotificationService
from jobscraper.storage.models import UserSubscriptionORM
from jobscraper.storage.repository import JobRepository
from jobscraper.storage.session import get_session_local
from sqlalchemy.exc import SQLAlchemyError


@dataclass()
class ScrapeResult:
    ok: bool = False
    total_jobs_found: int = 0
    new_jobs_processed: int = 0
    scraping_duration_seconds: float = 0.0
    stage: str = ""
    error: Optional[str] = None


async def scrape_and_create_notifications() -> ScrapeResult:
    result = ScrapeResult()
    try:
        session_factory = get_session_local()
        async with session_factory() as session:
            try:
                # get new jobs
                start_t = time.perf_counter()
                result.stage = "setup"
                search_scope = await get_scraping_scope(session)
                result.stage = "scraping"
                jobs = await scrape_all(search_scope)
                result.total_jobs_found = len(jobs)
                result.scraping_duration_seconds = time.perf_counter() - start_t
                logger.info(
                    f"Scraping finished in {result.scraping_duration_seconds:.2f}"
                )

                # save new jobs
                result.stage = "saving"
                repo = JobRepository(session)
                await repo.upsert_batch(jobs)

                # create notifications for subscriptions
                result.stage = "notifications"
                notification_service = NotificationService(session)
                new_jobs = await repo.get_new_jobs()  # fetch the unprocessed jobs
                await notification_service.create_for_new_jobs(new_jobs)
                for job in new_jobs:
                    job.status = JobStatus.PROCESSED

                await session.commit()  # commit all changes
                result.ok = True
                result.new_jobs_processed = len(new_jobs)
            except SQLAlchemyError as e:
                logger.error(f"Database error getting scraping scope: {e}")
                await session.rollback()
                result.error = f"Database error: {str(e)}"
            except aiohttp.ClientError as e:
                logger.error(f"Network error during scraping: {e}")
                await session.rollback()
                result.error = f"Network error: {str(e)}"
    except SQLAlchemyError as e:
        result.error = f"Session creation failed: {str(e)}"
    return result


async def scrape_all(scraping_scope: dict[str, list[str]]) -> list[Job]:
    all_jobs = []
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36 Indeed App 242.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "x-requested-with": "com.indeed.android.jobsearch",
        "sec-ch-ua-platform": '"Android"',
        "Referer": "https://www.indeed.com/",
    }
    async with aiohttp.ClientSession(
        headers=headers, cookie_jar=aiohttp.CookieJar(unsafe=True)
    ) as session:
        semaphore = asyncio.Semaphore(5)
        tasks = [
            scrape_domain(session, semaphore, location, scraping_scope[location])
            for location in scraping_scope
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, BaseException):
            logger.error(f"Scraping task failed: {res}")
            continue
        all_jobs.extend(res)
    return all_jobs


async def scrape_domain(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    location: str,
    categories: list[str],
) -> list[Job]:
    domain_jobs: list[Job] = []
    indeed = IndeedScraper(session, semaphore, location=location)
    for category in categories:
        for query in SEARCH_QUERIES[category]:
            try:
                jobs = await scrape_one(indeed, location, category, query)
                domain_jobs.extend(jobs)
                await asyncio.sleep(random.uniform(1.0, 5.0))
            except Exception as e:
                logger.error(str(e))
    return domain_jobs


async def scrape_one(
    indeed_scraper: IndeedScraper, location: str, category: str, query: str
) -> list[Job]:
    jobs = await indeed_scraper.scrape_job_list(query)
    for job in jobs:
        job.category = JobCategory(category)
        job.location = JobLocation(location)
    return jobs


async def get_scraping_scope(session: AsyncSession) -> dict[str, list[str]]:
    """Get active (location, category) pairs grouped by location."""
    scope = defaultdict(list)
    stmt = (
        select(UserSubscriptionORM.location, UserSubscriptionORM.category)
        .where(UserSubscriptionORM.is_active)
        .distinct()
    )
    unique_loc_cats = await session.execute(stmt)
    for loc, cat in unique_loc_cats:
        scope[loc].append(cat.value)
    return scope
