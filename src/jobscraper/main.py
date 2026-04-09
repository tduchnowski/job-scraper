import asyncio
import aiohttp
from jobscraper.models.job import Job
from jobscraper.storage.models import JobORM
from jobscraper.storage.repository import JobRepository
from jobscraper.utils.logger import setup_logger
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.session import SessionLocal
from sqlalchemy import select


async def main():
    setup_logger()
    jobs: list[Job] = []
    async with aiohttp.ClientSession() as session:
        indeed = IndeedScraper(session)
        jobs = await indeed.scrape_job_list("python developer", "Polska")

    # save jobs
    async with SessionLocal() as session:
        repo = JobRepository(session)
        for job in jobs:
            await repo.upsert(job)

    # scrape additional info
    async with SessionLocal() as session:
        query = select(JobORM).where(JobORM.status == "NEW")
        unprocessed = await session.stream(query)
        async for job in unprocessed.scalars():
            print(f"{job.title} | {job.company} | {job.url}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
