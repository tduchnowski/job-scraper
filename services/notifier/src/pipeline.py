from collections import defaultdict
from dataclasses import dataclass
import time
from typing import Optional
from redisaq import Producer
from sqlalchemy.ext.asyncio import AsyncSession
from services.notifier.src.notifications_generator import NotificationsGenerator
from services.shared.models.job import JobStatus
from services.shared.models.queue_message import JobUpdate, Payload
from services.shared.storage.models import NotificationORM
from services.shared.storage.repository import JobRepository, NotificationRepository


@dataclass
class NotifyResult:
    ok: bool = False
    jobs_processed: int = 0
    processing_duration: float = 0.0
    notifications_created: int = 0
    error: Optional[str] = None


async def make_notifications(
    session: AsyncSession,
    notifications_queue: Producer,
    job_status_queue: Producer,
    batch_size=500,
) -> NotifyResult:
    result = NotifyResult()
    job_repo = JobRepository(session)
    jobs_stream = job_repo.stream_new_jobs()
    notifications_gen = NotificationsGenerator(session)
    start_t = time.perf_counter()
    status_batch = []
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
            result.notifications_created += len(batch)

        result.jobs_processed += 1
        status_batch.append(
            JobUpdate(job_id=job.id, status=JobStatus.PROCESSED).model_dump(mode="json")
        )
        if len(status_batch) == batch_size:
            await job_status_queue.batch_enqueue(status_batch)
            status_batch = []
    if status_batch:
        await job_status_queue.batch_enqueue(status_batch)

    result.processing_duration = time.perf_counter() - start_t
    result.ok = True
    return result


@dataclass
class DispatchResult:
    ok: bool = False
    jobs_enqueued: int = 0
    duration: float = 0.0
    error: Optional[str] = None


async def make_messages(
    session: AsyncSession,
    message_queue: Producer,
    batch_size: int = 500,
    max_nots_per_user=10,
) -> DispatchResult:
    result = DispatchResult()
    repo = NotificationRepository(session)
    batch = []
    counter = defaultdict(int)
    start_t = time.perf_counter()
    async for notification in repo.get_pending_stream():
        user_id = notification.user_id
        counter[user_id] += 1
        if counter[user_id] <= max_nots_per_user:
            batch.append(
                make_telegram_notification(notification).model_dump(mode="json")
            )
        else:
            continue
        if len(batch) == batch_size:
            await message_queue.batch_enqueue(batch)
            result.jobs_enqueued += batch_size
            batch = []
    if batch:
        await message_queue.batch_enqueue(batch)
        result.jobs_enqueued += len(batch)

    result.duration = time.perf_counter() - start_t
    result.ok = True
    return result


def make_telegram_notification(notification: NotificationORM) -> Payload:
    # return TelegramNotification(chat_id=notification.user.chat_id, notification_id=notification.id, job=notification.job)
    return Payload(
        chat_id=notification.user.chat_id,
        message=f"New Job\n\nCompany: {notification.job.company}\nTitle: {notification.job.title}\nLocation: {notification.job.location}\nUrl: {notification.job.url}",
    )


def make_message_from_notifications(user_id: int, notifications: list[NotificationORM]):
    pass
