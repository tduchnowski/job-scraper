from dataclasses import dataclass
import time
from typing import Optional
import aiohttp
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from jobscraper.models.job import JobStatus
from jobscraper.services.notification_service import NotificationService
from jobscraper.services.scraping_service import get_scraping_scope, scrape_all
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
                result = await new_jobs_processor(session)
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


async def new_jobs_processor(session: AsyncSession) -> ScrapeResult:
    result = ScrapeResult()
    # get new jobs
    start_t = time.perf_counter()
    result.stage = "setup"
    search_scope = await get_scraping_scope(session)
    result.stage = "scraping"
    jobs = await scrape_all(search_scope)
    result.total_jobs_found = len(jobs)
    result.scraping_duration_seconds = time.perf_counter() - start_t
    logger.info(f"Scraping finished in {result.scraping_duration_seconds:.2f}")

    # save new jobs
    result.stage = "saving"
    repo = JobRepository(session)
    await repo.upsert_batch(jobs)

    # create notifications for subscriptions
    result.stage = "notifications"
    notification_service = NotificationService(session)
    new_jobs = await repo.get_new_jobs()  # fetch unprocessed jobs
    await notification_service.create_for_new_jobs(new_jobs)
    for job in new_jobs:
        job.status = JobStatus.PROCESSED

    await session.commit()  # commit all changes
    result.ok = True
    result.new_jobs_processed = len(new_jobs)
    return result
