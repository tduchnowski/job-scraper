import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from asyncio import Semaphore
from aiogram import Bot
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from jobscraper.bot.messages import send_batch_notification
from jobscraper.storage.models import NotificationORM
from jobscraper.storage.repository import NotificationRepository
from jobscraper.storage.session import get_session_local
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
        async with get_session_local()() as session:
            notifications = []
            notification_repo = NotificationRepository(session)
            try:
                # Get pending notifications (oldest first)
                notifications = await notification_repo.get_all_pending()
            except SQLAlchemyError as e:
                logger.error(f"Failed fetching pending notifications. {str(e)}")
                result.ok = False
                result.error = str(e)
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

            # process each user concurrently
            global_limiter = AsyncLimiter(20, 1)  # 20 messages per second
            sem = Semaphore(5)
            tasks = [
                process_notification_batch(
                    user_nots, notification_repo, bot, global_limiter, sem
                )
                for user_nots in user_notifications.values()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # process results
            for res in results:
                if isinstance(res, BaseException):
                    logger.error(f"Sending messages to user failed: {res}")
                else:
                    sent, failed = res
                    total_sent_count += sent
                    total_failed_count += failed

            result.notifications_sent = total_sent_count
            result.notifications_failed = total_failed_count
            result.total_notifications = total_sent_count + total_failed_count
            result.users_processed = len(user_notifications)
            result.ok = True

            return result
    except SQLAlchemyError as e:
        msg = f"Session creation failed: {str(e)}"
        logger.error(msg)
        result.error = msg
        return result


# TODO: refactor this shit
async def process_notification_batch(
    user_nots: list[NotificationORM],
    notification_repo: NotificationRepository,
    bot: Bot,
    global_limiter: AsyncLimiter,
    sem: Semaphore,
) -> tuple[int, int]:
    user = user_nots[0].user  # Get user from first notification
    sent_count = 0
    failed_count = 0
    user_limiter = AsyncLimiter(1, 1)
    try:
        async with sem:
            async with get_session_local()() as session:
                # TODO: reattach a user and notifications right away to this session

                # Group jobs in batches of 5
                job_batches = [
                    user_nots[i : i + 10] for i in range(0, len(user_nots), 10)
                ]
                for batch in job_batches:
                    try:
                        # Build message with multiple jobs
                        async with global_limiter:
                            async with user_limiter:
                                await send_batch_notification(bot, user, batch)

                        for notification in batch:
                            attached_notification = await session.merge(notification)
                            await notification_repo.mark_successful(
                                attached_notification
                            )

                        sent_count += len(batch)
                        logger.info(f"Sent {len(batch)} jobs to user {user.id}")
                    except TelegramForbiddenError:
                        logger.warning(f"Bot blocked by user {user.id}")
                        user = await session.merge(user)
                        user.is_active = False
                        for notification in batch:
                            notification_repo.mark_permanently_failed(
                                await session.merge(notification)
                            )
                        failed_count += len(batch)
                        break
                    except TelegramNotFound:
                        logger.warning(f"Chat not found for user {user.id}")
                        user = await session.merge(user)
                        user.is_active = False
                        for notification in batch:
                            notification_repo.mark_permanently_failed(
                                await session.merge(notification)
                            )
                        failed_count += len(batch)
                        break
                    except TelegramRetryAfter as e:
                        logger.warning(
                            f"Telegram rate limit for user {user.id}. Retry after {e.retry_after} seconds"
                        )
                        for notification in batch:
                            notification_repo.mark_failed(
                                await session.merge(notification),
                                retry_delay=e.retry_after,
                            )
                        failed_count += len(batch)
                    except (TelegramBadRequest, TelegramAPIError) as e:
                        logger.warning(
                            f"Failed to send to user. {user.id}: {e} ; batch={[job.id for job in batch]}"
                        )
                        for notification in batch:
                            notification_repo.mark_failed(
                                await session.merge(notification)
                            )
                        failed_count += len(batch)
                    except Exception as e:
                        logger.exception(f"Failed to send to user {user.id}: {e}")

                        for notification in batch:
                            notification_repo.mark_failed(
                                await session.merge(notification)
                            )

                        failed_count += len(batch)
                    finally:
                        try:
                            await session.commit()
                        except SQLAlchemyError as e:
                            logger.error(
                                f"Failed to commit batch for user {user.id}: {e}"
                            )
                            await session.rollback()
                            raise
    except SQLAlchemyError:
        logger.error(
            f"Couldn't create a new session for sending messages to user {user.id}"
        )
    return sent_count, failed_count
