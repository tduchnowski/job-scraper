import random
import asyncio
import aiohttp
from loguru import logger
from jobscraper.models.job import Job, JobCategory, JobLocation
from jobscraper.scrapers.indeed import IndeedScraper


async def scrape_all(
    locations: list[str], search_queries: dict[str, list[str]]
) -> list[Job]:
    all_jobs = []
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_domain(session, location, search_queries) for location in locations
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, BaseException):
            logger.error(f"Scraping task failed: {res}")
            continue
        all_jobs.extend(res)
    return all_jobs


async def scrape_domain(
    session: aiohttp.ClientSession, location: str, search_queries: dict[str, list[str]]
) -> list[Job]:
    domain_jobs: list[Job] = []
    indeed = IndeedScraper(session, location=location)
    for category in search_queries:
        for query in search_queries[category]:
            try:
                jobs = await scrape_one(indeed, location, category, query)
                domain_jobs.extend(jobs)
                await asyncio.sleep(random.uniform(1.0, 2.0))
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
    logger.info(
        f"Finished scrapping for location={location}, category={category}, query={query}"
    )
    return jobs
