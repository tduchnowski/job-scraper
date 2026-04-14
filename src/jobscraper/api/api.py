from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from aiogram import types

from jobscraper.bot import init_bot_and_dispatcher
from jobscraper.config.env import setup_env
from jobscraper.pipelines.dispatch_pipeline import dispatch_notifications
from jobscraper.pipelines.scrape_pipeline import scrape_and_create_notifications
from jobscraper.storage.session import set_session_local
from jobscraper.utils.logger import setup_logger
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    setup_env()
    set_session_local()

    app.state.bot, app.state.dp = init_bot_and_dispatcher()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates."""
    try:
        # parse update
        update_data = await request.json()
        update = types.Update(**update_data)

        # feed to dispatcher
        await app.state.dp.feed_update(app.state.bot, update)

    except Exception as e:
        logger.exception(f"Webhook error: {e}")
    finally:
        return Response(status_code=200)  # Always return 200 to Telegram


@app.post("/scrape")
async def scrape_jobs():
    """
    Triggers scraping of job boards and updating DB with new jobs and notifications
    This endpoint is intended for scheduler use only. Not publicly available.
    """
    logger.info("Starting scheduled job scraping")
    res = await scrape_and_create_notifications()
    logger.info(
        f"Scraping pipeline completed. Found {res.total_jobs_found}. Created new notifications for {res.new_jobs_processed} jobs"
    )
    return res


@app.post("/dispatch")
async def dispatch_jobs():
    """
    Triggers sending new jobs to users
    """
    logger.info("Notifications dispatch started")
    res = await dispatch_notifications(app.state.bot)
    logger.info(
        f"Dispatch completed: {res.notifications_sent} sent, {res.notifications_failed} failed"
    )
    return res


@app.post("/clean")
async def clean_db():
    """
    Cleans the database of all processed jobs and sent notifications
    """
    pass
