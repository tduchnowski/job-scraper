from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from aiogram import types

from jobscraper.bot import init_bot_and_dispatcher
from jobscraper.pipelines.dispatch_pipeline import dispatch_notifications
from jobscraper.pipelines.scrape_pipeline import scrape_and_create_notifications
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
        # parse update
        update_data = await request.json()
        update = types.Update(**update_data)

        # feed to dispatcher
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
    return await scrape_and_create_notifications()


@app.post("/dispatch")
async def dispatch_jobs():
    """
    Triggers sending new jobs to users
    """
    logger.info("Notifications dispatch started")
    return await dispatch_notifications(app.state.bot)


@app.post("/clean")
async def clean_db():
    """
    Cleans the database of all processed jobs and sent notifications
    """
    pass
