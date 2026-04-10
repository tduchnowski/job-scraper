from fastapi import FastAPI, Request, Response
from collections import defaultdict
from contextlib import asynccontextmanager
from aiogram import types
import aiohttp
from sqlalchemy import and_, select
from sqlalchemy.orm.strategy_options import selectinload
from datetime import datetime, timedelta, timezone

from jobscraper.bot import init_bot_and_dispatcher
from jobscraper.models.job import JobStatus
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.models import (
    NotificationORM,
    UserORM,
    UserSubscriptionORM,
)
from jobscraper.storage.repository import JobRepository
from jobscraper.storage.session import SessionLocal
from jobscraper.utils.logger import setup_logger
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    app.state.bot, app.state.dp = init_bot_and_dispatcher()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates."""
    try:
        # Parse update
        update_data = await request.json()
        update = types.Update(**update_data)

        # Feed to dispatcher
        await app.state.dp.feed_update(app.state.bot, update)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
    finally:
        return Response(status_code=200)  # Always return 200 to Telegram


@app.post("/scrape")
async def scrape_jobs():
    """
    Triggers scraping of job boards and updating DB with new jobs
    This endpoint is intended for scheduler use only. Not publicly available.
    """
    logger.info("Starting scheduled job scraping")
    try:
        # scrape job boards
        async with aiohttp.ClientSession() as session:
            indeed = IndeedScraper(session)
            jobs = await indeed.scrape_job_list("python developer", "Poland")

        async with SessionLocal() as session:
            # save new jobs
            repo = JobRepository(session)
            for job in jobs:
                await repo.upsert(job)

            # create notifications for subscriptions
            new_jobs = await repo.get_new_jobs()  # fetch the unprocessed jobs
            for job in new_jobs:
                query = (
                    select(UserORM)
                    .join(
                        UserSubscriptionORM, UserSubscriptionORM.user_id == UserORM.id
                    )
                    .where(
                        and_(
                            UserSubscriptionORM.is_active,
                            UserSubscriptionORM.category == job.category,
                            UserSubscriptionORM.location == job.location,
                            UserSubscriptionORM.last_notified_at < job.created_at,
                        )
                    )
                )
                users_to_notify = await session.execute(query)
                for user in users_to_notify.scalars():
                    notification = NotificationORM(user_id=user.id, job_id=job.id)
                    session.add(notification)
                await session.commit()
                job.status = JobStatus.PROCESSED
            await session.commit()

        return {
            "ok": True,
            "jobs_scraped": len(jobs),
        }
    except aiohttp.ClientError as e:
        logger.error(f"Network error during scraping: {e}")
        return {"ok": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/dispatch")
async def dispatch_jobs():
    """
    Triggers sending new jobs to users
    """
    async with SessionLocal() as session:
        # Get pending notifications (oldest first)
        stmt = (
            select(NotificationORM)
            .where(
                and_(
                    NotificationORM.status == "pending",
                    NotificationORM.next_attempt_at <= datetime.now(timezone.utc),
                )
            )
            .order_by(
                NotificationORM.created_at.asc()  # Oldest first
            )
            .limit(100)
            .options(
                selectinload(NotificationORM.user), selectinload(NotificationORM.job)
            )
        )

        result = await session.execute(stmt)
        notifications = result.scalars().all()

        if not notifications:
            logger.debug("No pending notifications")
            return {"ok": True, "notifications_sent": 0}

        # Group by user
        user_notifications = defaultdict(list)
        for notification in notifications:
            user_notifications[notification.user_id].append(notification)

        sent_count = 0
        failed_count = 0

        # Process each user
        for user_id, user_nots in user_notifications.items():
            user = user_nots[0].user  # Get user from first notification

            # Group jobs in batches of 5
            job_batches = [user_nots[i : i + 5] for i in range(0, len(user_nots), 5)]

            for batch in job_batches:
                try:
                    # Build message with multiple jobs
                    jobs_text = "\n\n---\n\n".join(
                        [
                            f"📌 *{n.job.title}*\n"
                            f"🏢 {n.job.company}\n"
                            f"💰 {n.job.salary or 'Not specified'}\n"
                            f"📍 {n.job.location}\n"
                            f"🔗 [View]({n.job.url})"
                            for n in batch
                        ]
                    )

                    message = (
                        f"🎉 *New job alert!*\n\n"
                        f"{jobs_text}\n\n"
                        f"Use /subscribe to manage preferences"
                    )

                    # Send to Telegram
                    await app.state.bot.send_message(
                        chat_id=user.chat_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )

                    # Mark as sent
                    for notification in batch:
                        notification.status = "sent"
                        notification.last_attempt_at = datetime.now(timezone.utc)

                    sent_count += len(batch)
                    logger.info(f"Sent {len(batch)} jobs to user {user_id}")

                except Exception as e:
                    logger.error(f"Failed to send to user {user_id}: {e}")

                    # Mark as failed with retry logic
                    for notification in batch:
                        notification.attempts += 1
                        notification.last_attempt_at = datetime.now(timezone.utc)

                        if notification.attempts >= 3:
                            notification.status = "failed"
                            logger.warning(
                                f"Notification {notification.id} failed after 3 attempts"
                            )
                        else:
                            # Retry in exponential backoff: 5min, 30min, 2h
                            delay = 60 * (2**notification.attempts)  # 2, 4, 8 minutes
                            notification.next_attempt_at = datetime.now(
                                timezone.utc
                            ) + timedelta(seconds=delay)

                    failed_count += len(batch)

        await session.commit()

        logger.info(f"Dispatch completed: {sent_count} sent, {failed_count} failed")
        return {
            "ok": True,
            "notifications_sent": sent_count,
            "notifications_failed": failed_count,
        }
