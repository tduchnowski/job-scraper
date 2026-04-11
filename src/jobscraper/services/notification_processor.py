from typing import Tuple
from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from jobscraper.bot.messages import send_batch_notification
from jobscraper.storage.models import NotificationORM
from jobscraper.storage.repository import NotificationRepository


async def process_notification_batch(
    session: AsyncSession,
    user_nots: list[NotificationORM],
    notification_repo: NotificationRepository,
    bot: Bot,
) -> Tuple[int, int]:
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
