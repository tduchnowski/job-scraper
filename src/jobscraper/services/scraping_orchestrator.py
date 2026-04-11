import asyncio
import aiohttp
from loguru import logger
from jobscraper.config.scraping_config import INDEED_DOMAINS, SEARCH_QUERIES
from jobscraper.models.job import Job, JobCategory, JobLocation
from jobscraper.scrapers.indeed import IndeedScraper


async def scrape_all() -> list[Job]:
    all_jobs: list[Job] = []
    async with aiohttp.ClientSession() as session:
        for location in INDEED_DOMAINS:
            indeed = IndeedScraper(session, location=location)
            for category in SEARCH_QUERIES:
                for query in SEARCH_QUERIES[category]:
                    try:
                        jobs = await indeed.scrape_job_list(query)
                        all_jobs.extend(jobs)
                        for job in jobs:
                            job.category = JobCategory(category)
                            job.location = JobLocation(location)
                        await asyncio.sleep(5)
                        logger.info(
                            f"Finished querying: location={location}, category={category}, query={query}"
                        )
                    except Exception as e:
                        logger.error(str(e))
    return all_jobs
