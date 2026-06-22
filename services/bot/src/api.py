import os
import asyncio

from typing import Annotated
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response, status
from fastapi.responses import JSONResponse
from aiogram import types, Bot, Dispatcher

from services.bot.src.middleware import UserTrackingMiddleware
from services.bot.src.consumers.notification import (
    MessageProcessor,
    create_notification_consumer,
)
from services.bot.src.producers.user_activity import create_user_activity_producer
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

            # set up Redis
            redis_host = os.getenv("REDIS_HOST", "")
            redis_port = os.getenv("REDIS_PORT", "")
            # message queue consumer
            redis_notification_topic = os.getenv("REDIS_NOTIFICATION_TOPIC", "")
            redis_notification_group = os.getenv("REDIS_NOTIFICATION_GROUP_NAME", "")
            app.state.redis_consumer = create_notification_consumer(
                redis_host,
                redis_port,
                redis_notification_topic,
                redis_notification_group,
            )
            await app.state.redis_consumer.connect()
            message_processor = MessageProcessor(app.state.bot, app.state.dp)
            consumer_task = asyncio.create_task(
                app.state.redis_consumer.consume(message_processor.process)
            )

            # user update producer
            redis_user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
            app.state.redis_producer = create_user_activity_producer(
                redis_host, redis_port, redis_user_activity_topic
            )
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

    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_TOKEN")
    secret_verified = TelegramSecretVerifier(webhook_secret)

    @app.post(
        "/webhook", dependencies=[Depends(secret_verified.verify_telegram_secret)]
    )
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

        return Response(status_code=200)  # always return 200, unless unauthorized

    return app


class TelegramSecretVerifier:
    def __init__(self, secret):
        self.secret = secret

    async def verify_telegram_secret(
        self,
        request: Request,
        x_telegram_bot_api_secret_token: Annotated[
            str | None, Header(include_in_schema=False)
        ] = None,
    ):
        if (
            x_telegram_bot_api_secret_token is None
            or x_telegram_bot_api_secret_token != self.secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )
