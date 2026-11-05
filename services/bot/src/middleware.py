# from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from redis.asyncio import Redis
from redisaq import Producer

from services.shared.models.queue_message import UserActivity


class UserTrackingMiddleware(BaseMiddleware):
    def __init__(self, redis_client: Redis, queue_producer: Producer, ttl: int = 300):
        self.queue_producer = queue_producer
        self.redis_client = redis_client
        self.cache_ttl = ttl

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        chat = data.get("event_chat")

        if user and chat:
            was_set = await self.redis_client.set(
                f"activity:{user.id}", "1", ex=self.cache_ttl, nx=True
            )
            if was_set:
                user_update = UserActivity(
                    user_id=user.id, chat_id=chat.id, username=user.username
                )
                await self.queue_producer.enqueue(user_update.model_dump())

        return await handler(event, data)
