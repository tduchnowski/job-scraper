from fastapi import FastAPI, Request, Response
from collections import defaultdict
from contextlib import asynccontextmanager
from aiogram import types
import aiohttp

from jobscraper.bot import init_bot_and_dispatcher
from jobscraper.services.notification_processor import process_notification_batch
from jobscraper.services.notification_service import NotificationService
from jobscraper.services.scraping_orchestrator import scrape_all
from jobscraper.storage.repository import JobRepository, NotificationRepository
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
    Triggers scraping of job boards and updating DB with new jobs and notifications
    This endpoint is intended for scheduler use only. Not publicly available.
    """
    logger.info("Starting scheduled job scraping")
    try:
        jobs = await scrape_all()

        async with SessionLocal() as session:
            # save new jobs
            repo = JobRepository(session)
            await repo.upsert_batch(jobs)

            # create notifications for subscriptions
            notification_service = NotificationService(session)
            new_jobs = await repo.get_new_jobs()  # fetch the unprocessed jobs
            await notification_service.create_for_new_jobs(new_jobs)
            logger.info("Created new notifications")

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

    TODO: mark all jobs as processed in the end
    """
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
                session, user_nots, notification_repo, app.state.bot
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


@app.post("/clean")
async def clean_db():
    """
    Cleans the database of all processed jobs and sent notifications
    """
