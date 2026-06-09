import os
import asyncio

from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from aiogram import types, Bot, Dispatcher

from services.bot.src.middleware import UserTrackingMiddleware
from services.bot.src.notifications_consumer import MessageProcessor, create_consumer
from services.bot.src.queue_user import create_producer
from services.shared.utils.logger import setup_logger
from loguru import logger


def init_bot_and_dispatcher():
    """Initialize bot and dispatcher together."""
    from services.bot.src.handlers import register_handlers

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    bot = Bot(token=token)
    dp = Dispatcher()
    register_handlers(dp)

    return bot, dp


def create_app(bot=None, dp=None):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        consumer_task = None
        if bot is None and dp is None:
            setup_logger()
            app.state.bot, app.state.dp = init_bot_and_dispatcher()
            app.state.webhook_token = os.getenv("TELEGRAM_WEBHOOK_TOKEN")
            app.state.api_key = os.getenv("API_KEY")

            # message queue consumer
            app.state.redis_consumer = create_consumer()
            await app.state.redis_consumer.connect()
            message_processor = MessageProcessor(app.state.bot, app.state.dp)
            consumer_task = asyncio.create_task(
                app.state.redis_consumer.consume(message_processor.process)
            )

            # user update producer
            app.state.redis_producer = create_producer()
            await app.state.redis_producer.connect()
            app.state.dp.message.middleware(
                UserTrackingMiddleware(app.state.redis_producer)
            )

        yield

        if consumer_task:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

        if app.state.redis_consumer:
            await app.state.redis_consumer.close()
        if app.state.redis_producer:
            await app.state.redis_producer.close()

    app = FastAPI(lifespan=lifespan)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc

        logger.exception(f"Unhandled error: {exc}")

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    @app.get("/health")
    async def health():
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
        }

        return health_status

    @app.post("/webhook")
    async def webhook(request: Request):
        """Handle Telegram webhook updates."""
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != app.state.webhook_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            # parse update
            update_data = await request.json()
            update = types.Update(**update_data)

            # feed to dispatcher
            await app.state.dp.feed_update(app.state.bot, update)

        except Exception as e:
            logger.exception(f"Webhook error: {e}")

        return Response(status_code=200)  # always return 200, unless unauthorized

    async def verify_api_key(request: Request):
        api_key = request.headers.get("X-API-Key")
        if api_key != app.state.api_key:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return True

    return app
