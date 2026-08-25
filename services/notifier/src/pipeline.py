from dataclasses import dataclass
import time
from typing import Optional
from redisaq import Producer
from sqlalchemy.ext.asyncio import AsyncSession
from services.notifier.src.notifications_generator import NotificationsGenerator
from services.shared.storage.repository import JobRepository


@dataclass
class NotifyResult:
    ok: bool = False
    jobs_processed: int = 0
    processing_duration: float = 0.0
    notifications_created: int = 0
    error: Optional[str] = None


async def make_notifications(
    session: AsyncSession, notifications_queue: Producer, batch_size=500
) -> NotifyResult:
    result = NotifyResult()
    job_repo = JobRepository(session)
    jobs_stream = job_repo.stream_new_jobs()
    notifications_gen = NotificationsGenerator(session)
    start_t = time.perf_counter()
    async for job in jobs_stream:
        batch = []
        async for notification in notifications_gen.create_stream_for_job(job):
            batch.append(notification.model_dump(mode="json"))
            if len(batch) == batch_size:
                await notifications_queue.batch_enqueue(batch)
                result.notifications_created += batch_size
                batch = []
        if batch:
            await notifications_queue.batch_enqueue(batch)
        result.jobs_processed += 1
        await job_repo.update_status(job.id, "processed")

    result.processing_duration = time.perf_counter() - start_t
    result.ok = True
    return result
