import asyncio
from contextlib import asynccontextmanager
from aiogram import Dispatcher, types
from aiogram.filters import Command
import aiohttp
from fastapi import FastAPI, Request
from sqlalchemy import and_, select
from sqlalchemy.orm.strategy_options import selectinload
from datetime import datetime, timezone

from jobscraper.api.bot import create_bot
from jobscraper.scrapers.indeed import IndeedScraper
from jobscraper.storage.models import JobORM, UserORM, UserSubscriptionORM
from jobscraper.storage.repository import JobRepository
from jobscraper.storage.session import SessionLocal
from jobscraper.utils.logger import setup_logger
from loguru import logger

setup_logger()
bot = create_bot()
dp = Dispatcher()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Save user to database
    async with SessionLocal() as session:
        # Check if user exists
        if not message.from_user:
            return
        user = await session.get(UserORM, message.from_user.id)

        if not user:
            # Create new user
            user = UserORM(
                id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                created_at=datetime.now(timezone.utc),
                last_interaction=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()
            logger.info(f"New user saved: {user.id} ({user.username})")
        else:
            # Update last interaction
            user.last_interaction = datetime.now(timezone.utc)
            await session.commit()
            logger.debug(f"User updated: {user.id}")

    await message.answer(
        "Hi! Welcome to Job Notifier Bot. Use /subscribe to get job notifications."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start bot polling in background
    logger.info("start bot polling")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Cleanup on shutdown
    polling_task.cancel()
    try:
        await asyncio.wait_for(polling_task, timeout=10.0)
        logger.info("Bot polling stopped")
    except asyncio.TimeoutError:
        logger.warning("Bot polling timeout, forcing stop")
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")

    await bot.session.close()
    logger.info("Bot session closed")


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    """
    Telegram bot updates
    """
    return {"ok": True}


@app.post("/scrape")
async def scrape_jobs():
    """
    Triggers scraping of job boards and updating DB with new jobs
    This endpoint is intended for scheduler use only. Not publicly available.
    """
    logger.info("Starting scheduled job scraping")
    try:
        async with aiohttp.ClientSession() as session:
            indeed = IndeedScraper(session)
            jobs = await indeed.scrape_job_list("python developer", "Polska")

        async with SessionLocal() as session:
            repo = JobRepository(session)
            for job in jobs:
                await repo.upsert(job)

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
    logger.info("Starting scheduled dispatcher")
    async with SessionLocal() as session:
        subs_query = select(UserSubscriptionORM).options(
            selectinload(UserSubscriptionORM.user)
        )
        subs = await session.execute(subs_query)
        for sub in subs.scalars():
            stmt = select(JobORM).where(
                and_(
                    JobORM.status == "NEW",
                    JobORM.location == sub.location,
                    JobORM.category == sub.category,
                    JobORM.created_at > sub.last_notified_at,
                )
            )
            matching_jobs = (await session.execute(stmt)).scalars().all()
            logger.info(f"User: {sub.user.username}")
            logger.info(f"Found {len(matching_jobs)} for user: {sub.user.username}")
            for job in matching_jobs:
                message = (
                    f"🎉 New {job.category} job in {job.location}!\n\n"
                    f"📌 *{job.title}*\n"
                    f"🏢 {job.company}\n"
                    f"💰 {job.salary or 'Not specified'}\n"
                    f"🔗 [Apply here]({job.url})\n\n"
                )
                try:
                    await bot.send_message(
                        chat_id=sub.user.chat_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=False,
                    )

                    # Update last_notified_at
                    sub.last_notified_at = datetime.now(timezone.utc)
                    await session.commit()

                    logger.info(f"Sent job {job.id} to user {sub.user.id}")

                except Exception as e:
                    logger.error(f"Failed to send to {sub.user.id}: {e}")
    return {"ok": True}
