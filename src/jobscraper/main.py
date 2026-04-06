import asyncio
import aiohttp
from jobscraper.models.job import Job
from jobscraper.storage.repository import JobRepository
from jobscraper.utils.logger import setup_logger
from loguru import logger
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.session import SessionLocal


async def main():
    setup_logger()
    logger.info("Pipeline started")
    jobs: list[Job] = []
    async with aiohttp.ClientSession() as session:
        indeed = IndeedScraper(session)
        jobs = await indeed.scrape_job_list("python developer", "Polska")
    async with SessionLocal() as session:
        repo = JobRepository(session)
        for job in jobs:
            await repo.upsert(job)


if __name__ == "__main__":
    asyncio.run(main())
