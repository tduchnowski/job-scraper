import os
import asyncio
import json

from typing import Annotated
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response, status
from aiogram import types, Bot, Dispatcher
from pydantic import ValidationError
from redisaq import Consumer, Producer

from services.bot.src.middleware import UserTrackingMiddleware
from services.bot.src.consumers.notification import UserMessageProcessor
from services.bot.src.subscription_service import SubscriptionService
from services.shared.storage.session import set_session_local
from services.shared.utils.logger import setup_logger
from services.shared.infra.redis import create_consumer, create_producer
from loguru import logger


def init_bot_and_dispatcher(subscription_service: SubscriptionService):
    """Initialize bot and dispatcher together."""
    from services.bot.src.handlers import register_handlers

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    bot = Bot(token=token)
    dp = Dispatcher()
    register_handlers(dp, subscription_service)

    return bot, dp


def create_app(bot=None, dp=None):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        user_messages_consumer_task = None
        producers: list[Producer] = []  # list of Redis queue producers
        consumers: list[Consumer] = []  # list of Redis consumers
        background_tasks: list[asyncio.Task] = []
        if bot is None and dp is None:
            setup_logger()
            set_session_local()

            redis_url = os.getenv("REDIS_URL", "")

            # producer - user subscriptions
            subscription_topic = os.getenv("REDIS_SUBSCRIPTIONS_TOPIC", "")
            app.state.subscription_producer = create_producer(
                redis_url, subscription_topic
            )
            await app.state.subscription_producer.connect()
            producers.append(app.state.subscription_producer)

            subs_service = SubscriptionService(app.state.subscription_producer)
            app.state.bot, app.state.dp = init_bot_and_dispatcher(subs_service)

            app.state.webhook_token = os.getenv("TELEGRAM_WEBHOOK_TOKEN")
            redis_telegram_group = os.getenv("REDIS_TELEGRAM_WORKERS_GROUP_NAME", "")

            # producer - notification updates queue
            notification_status_topic = os.getenv("REDIS_NOTIFICATION_STATUS_TOPIC", "")
            app.state.notification_status_producer = create_producer(
                redis_url, notification_status_topic
            )
            await app.state.notification_status_producer.connect()
            producers.append(app.state.notification_status_producer)

            message_processor = UserMessageProcessor(
                app.state.bot, app.state.notification_status_producer
            )

            # consumer - messages for users
            redis_user_messages_topic = os.getenv("REDIS_USER_MESSAGES_TOPIC", "")
            app.state.user_messages_consumer = create_consumer(
                redis_url,
                redis_user_messages_topic,
                redis_telegram_group,
            )
            await app.state.user_messages_consumer.connect()
            consumers.append(app.state.user_messages_consumer)

            user_messages_consumer_task = asyncio.create_task(
                app.state.user_messages_consumer.consume(message_processor.process)
            )
            background_tasks.append(user_messages_consumer_task)

            # producer - user updates
            redis_user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
            app.state.user_activity_producer = create_producer(
                redis_url, redis_user_activity_topic
            )
            await app.state.user_activity_producer.connect()
            producers.append(app.state.user_activity_producer)

            # producer - subscription update
            redis_subscription_topic = os.getenv("REDIS_SUBSCRIPTIONS_TOPIC", "")
            app.state.subscription_producer = create_producer(
                redis_url, redis_subscription_topic
            )
            await app.state.subscription_producer.connect()
            producers.append(app.state.subscription_producer)

            # add middleware
            app.state.dp.message.middleware(
                UserTrackingMiddleware(app.state.user_activity_producer)
            )

        yield

        for background_task in background_tasks:
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass

        for producer in producers:
            try:
                await producer.close()
            except Exception:
                logger.exception(
                    "Failed to close a producer", extra={"topic": producer.topic}
                )

        for consumer in consumers:
            try:
                await consumer.close()
            except Exception:
                logger.exception(
                    "Failed to close a consumer", extra={"topic": consumer.topic}
                )

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    async def health():
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            # TODO: add redis connection check
        }

        return health_status

    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_TOKEN")
    secret_verified = TelegramSecretVerifier(webhook_secret)

    @app.post(
        "/webhook", dependencies=[Depends(secret_verified.verify_telegram_secret)]
    )
    async def webhook(request: Request):
        """Handle Telegram webhook updates."""
        update = None
        try:
            # parse update
            update_data = await request.json()
            update = types.Update(**update_data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Received non-JSON structure as an update")
        except ValidationError as e:
            logger.exception(
                "Telegram Update payload failed schema validation",
                extra={"validation_errors": e.errors(), "raw_payload": update},
            )
        except (TypeError, ValueError) as e:
            logger.warning(
                "Received invalid JSON structure", extra={"error_detail": str(e)}
            )

        if update is None:
            return Response(status_code=200)

        try:
            # feed to dispatcher
            await app.state.dp.feed_update(app.state.bot, update)
        except Exception:
            logger.exception(
                "Unexpected webhook error",
                extra={"telegram_update": update.model_dump()},
            )

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
