import asyncio
import random
import time
import aiohttp

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger
from asyncio import Semaphore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redisaq import Producer
from datetime import datetime, timezone

from services.scraper.scrapers.indeed import IndeedScraper
from services.scraper.scrapers.scraper_base import Scraper
from services.shared.config.scraping import SEARCH_QUERIES
from services.shared.models.job import JobCategory, JobLocation
from services.shared.storage.models import UserSubscriptionORM


@dataclass()
class ScrapeResult:
    ok: bool = False
    total_jobs_found: int = 0
    scraping_duration_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class ScrapeDomainResult:
    ok: bool = False
    location: str = ""
    total_jobs_found: int = 0
    scraping_duration_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class ScrapeSiteResult:
    ok: bool = False
    site: str = ""
    domain_results: list[ScrapeDomainResult] = field(default_factory=list)


SCRAPERS_MAP: dict[str, type[Scraper]] = {"indeed": IndeedScraper}


async def find_new_jobs(
    job_queue: Producer, search_scope: dict[str, list[str]], sites: list[str]
) -> list[ScrapeSiteResult]:
    sem = Semaphore(5)
    tasks = [scrape_from_site(site, job_queue, sem, search_scope) for site in sites]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return filter_results(results)


async def scrape_from_site(
    site: str, job_queue: Producer, sem: Semaphore, search_scope: dict[str, list[str]]
) -> ScrapeSiteResult:
    result = ScrapeSiteResult(site=site)
    if site not in SCRAPERS_MAP:
        logger.warning(f"{site} is not present in SCRAPERS_MAP. Skipping")
        return result

    scraper_class = SCRAPERS_MAP[site]
    headers = get_headers(site)
    async with aiohttp.ClientSession(
        headers=headers, cookie_jar=aiohttp.CookieJar(unsafe=True)
    ) as session:
        tasks = []
        for location, categories in search_scope.items():
            scraper = scraper_class(session, sem, location)
            tasks.append(scrape_domain(scraper, job_queue, categories))
        domain_results = await asyncio.gather(*tasks, return_exceptions=True)
    domain_results = filter_results(domain_results)
    result.domain_results = domain_results
    result.ok = True
    return result


async def scrape_domain(
    scraper: Scraper, queue: Producer, categories: list[str], wait_min=1.0, wait_max=5.0
) -> ScrapeDomainResult:
    start_t = time.perf_counter()
    res = ScrapeDomainResult()
    res.location = scraper.location
    jobs_found_counter = 0
    for category in categories:
        for query in SEARCH_QUERIES[category]:
            jobs = await scraper.scrape_job_list(query)
            for job in jobs:
                job.category = JobCategory[category]
                job.location = JobLocation[scraper.location]
                job.scraped_at = datetime.now(timezone.utc)
            serialized_jobs = [job.model_dump(mode="json") for job in jobs]
            await queue.batch_enqueue(serialized_jobs)
            jobs_found_counter += len(serialized_jobs)
            await asyncio.sleep(random.uniform(wait_min, wait_max))

    res.ok = True
    res.total_jobs_found = jobs_found_counter
    res.scraping_duration_seconds = time.perf_counter() - start_t
    return res


def get_headers(scraper_type: str):
    if scraper_type == "indeed":
        return {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36 Indeed App 242.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "x-requested-with": "com.indeed.android.jobsearch",
            "sec-ch-ua-platform": '"Android"',
            "Referer": "https://www.indeed.com/",
        }


def filter_results(results: list) -> list:
    """Filters out and logs exceptions in a list of results"""
    filtered_results = []
    for res in results:
        if isinstance(res, Exception):
            logger.exception(res)
        else:
            filtered_results.append(res)
    return filtered_results


# async def new_jobs_processor(session: AsyncSession) -> ScrapeResult:
#     result = ScrapeResult()
#     # get new jobs
#     start_t = time.perf_counter()
#     search_scope = await get_scraping_scope(session)
#     jobs = await scrape_all(search_scope)
#     result.total_jobs_found = len(jobs)
#     result.scraping_duration_seconds = time.perf_counter() - start_t
#     logger.info(f"Scraping finished in {result.scraping_duration_seconds:.2f}")
#
#     # save new jobs
#     repo = JobRepository(session)
#     await repo.upsert_batch(jobs)
#     return result


async def get_scraping_scope(session: AsyncSession) -> dict[str, list[str]]:
    """
    Returns a dictionary with location as key and a list of categories as values

    The purpose is to filter out categories that don't need to be scraped, based on users active subscriptions
    """
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
