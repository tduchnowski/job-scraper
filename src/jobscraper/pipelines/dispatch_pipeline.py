from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from aiogram import Bot
from loguru import logger
from jobscraper.bot.messages import send_batch_notification
from jobscraper.storage.models import NotificationORM
from jobscraper.storage.repository import NotificationRepository
from jobscraper.storage.session import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass()
class DispatchResult:
    ok: bool = True
    notifications_sent: int = 0
    notifications_failed: int = 0
    total_notifications: int = 0
    error: Optional[str] = None
    users_processed: int = 0


async def dispatch_notifications(bot: Bot):
    async with SessionLocal() as session:
        # Get pending notifications (oldest first)
        notification_repo = NotificationRepository(session)
        notifications = await notification_repo.get_all_pending()

        if not notifications:
            logger.debug("No pending notifications")
            return {"ok": True, "notifications_sent": 0}

        # Group by user
        user_notifications = defaultdict(list)
        for notification in notifications:
            user_notifications[notification.user_id].append(notification)

        total_sent_count = 0
        total_failed_count = 0

        # Process each user
        for _, user_nots in user_notifications.items():
            sent, failed = await process_notification_batch(
                session, user_nots, notification_repo, bot
            )
            total_sent_count += sent
            total_failed_count += failed

        logger.info(
            f"Dispatch completed: {total_sent_count} sent, {total_failed_count} failed"
        )
        return {
            "ok": True,
            "notifications_sent": total_sent_count,
            "notifications_failed": total_failed_count,
        }


async def process_notification_batch(
    session: AsyncSession,
    user_nots: list[NotificationORM],
    notification_repo: NotificationRepository,
    bot: Bot,
) -> tuple[int, int]:
    user = user_nots[0].user  # Get user from first notification
    sent_count = 0
    failed_count = 0

    # Group jobs in batches of 5
    job_batches = [user_nots[i : i + 5] for i in range(0, len(user_nots), 5)]
    for batch in job_batches:
        try:
            # Build message with multiple jobs
            await send_batch_notification(bot, user, batch)

            for notification in batch:
                await notification_repo.mark_successful(notification)

            sent_count += len(batch)
            logger.info(f"Sent {len(batch)} jobs to user {user.id}")

        except Exception as e:
            logger.error(f"Failed to send to user {user.id}: {e}")

            for notification in batch:
                await notification_repo.mark_failed(notification)

            failed_count += len(batch)
        finally:
            await session.commit()
    return sent_count, failed_count
