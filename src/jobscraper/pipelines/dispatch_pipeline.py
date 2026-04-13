from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from aiogram import Bot
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from jobscraper.bot.messages import send_batch_notification
from jobscraper.storage.models import NotificationORM
from jobscraper.storage.repository import NotificationRepository
from jobscraper.storage.session import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from aiolimiter import AsyncLimiter
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)


@dataclass()
class DispatchResult:
    ok: bool = True
    notifications_sent: int = 0
    notifications_failed: int = 0
    total_notifications: int = 0
    error: Optional[str] = None
    users_processed: int = 0


async def dispatch_notifications(bot: Bot):
    result = DispatchResult()
    try:
        async with SessionLocal() as session:
            notifications = []
            notification_repo = NotificationRepository(session)
            try:
                # Get pending notifications (oldest first)
                notifications = await notification_repo.get_all_pending()
            except SQLAlchemyError as e:
                logger.error(f"Failed fetching pending notifications. {str(e)}")
                return result

            if not notifications:
                logger.debug("No pending notifications")
                result.ok = True
                return result

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

            result.notifications_sent = total_sent_count
            result.notifications_failed = total_failed_count
            result.total_notifications = total_sent_count + total_failed_count
            result.users_processed = len(user_notifications)
            result.ok = True

            logger.info(
                f"Dispatch completed: {total_sent_count} sent, {total_failed_count} failed"
            )
            return result
    except SQLAlchemyError as e:
        msg = f"Session creation failed: {str(e)}"
        logger.error(msg)
        result.error = msg
        return result


async def process_notification_batch(
    session: AsyncSession,
    user_nots: list[NotificationORM],
    notification_repo: NotificationRepository,
    bot: Bot,
) -> tuple[int, int]:
    user = user_nots[0].user  # Get user from first notification
    sent_count = 0
    failed_count = 0
    user_limiter = AsyncLimiter(1, 1)

    # Group jobs in batches of 5
    job_batches = [user_nots[i : i + 10] for i in range(0, len(user_nots), 10)]
    for batch in job_batches:
        try:
            # Build message with multiple jobs
            async with user_limiter:
                await send_batch_notification(bot, user, batch)

            for notification in batch:
                await notification_repo.mark_successful(notification)

            sent_count += len(batch)
            logger.info(f"Sent {len(batch)} jobs to user {user.id}")
        except TelegramForbiddenError:
            logger.warning(f"Bot blocked by user {user.id}")
            user.is_active = False
            for notification in batch:
                notification_repo.mark_permanently_failed(notification)
            failed_count += len(batch)
            break
        except TelegramNotFound:
            logger.warning(f"Chat not found for user {user.id}")
            user.is_active = False
            for notification in batch:
                notification_repo.mark_permanently_failed(notification)
            failed_count += len(batch)
            break
        except TelegramRetryAfter as e:
            logger.warning(
                f"Telegram rate limit for user {user.id}. Retry after {e.retry_after} seconds"
            )
            for notification in batch:
                notification_repo.mark_failed(notification, retry_delay=e.retry_after)
            failed_count += len(batch)
        except (TelegramBadRequest, TelegramAPIError) as e:
            logger.warning(f"Failed to send to user {user.id}: {e}")
            for notification in batch:
                notification_repo.mark_failed(notification)
            failed_count += len(batch)
        except Exception as e:
            logger.error(f"Failed to send to user {user.id}: {e}")

            for notification in batch:
                notification_repo.mark_failed(notification)

            failed_count += len(batch)
        finally:
            try:
                await session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Failed to commit batch for user {user.id}: {e}")
                await session.rollback()
                raise
    return sent_count, failed_count
