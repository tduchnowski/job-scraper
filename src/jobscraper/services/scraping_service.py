import asyncio
from collections import defaultdict
import random
import aiohttp
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jobscraper.config.scraping_config import SEARCH_QUERIES
from jobscraper.models.job import Job, JobCategory, JobLocation
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.models import UserSubscriptionORM


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
    wait_min: float = 1.0,
    wait_max: float = 5.0,
) -> list[Job]:
    domain_jobs: list[Job] = []
    indeed = IndeedScraper(session, semaphore, location=location)
    for category in categories:
        for query in SEARCH_QUERIES[category]:
            try:
                jobs = await scrape_one(indeed, location, category, query)
                domain_jobs.extend(jobs)
                await asyncio.sleep(random.uniform(wait_min, wait_max))
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
