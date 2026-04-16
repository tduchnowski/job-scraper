import asyncio
import time
from aiogram import BaseMiddleware
from aiogram.types import Chat, User
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.storage.repository import UserRepository
from jobscraper.storage.session import get_session_local


class UserTrackingMiddleware(BaseMiddleware):
    def __init__(self):
        self.cache = {}  # user_id -> time

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        chat = data.get("event_chat")

        if user and chat:
            time_now = time.time()
            user_last_seen = self.cache.get(user.id, 0)
            if time_now - user_last_seen > 60:
                self.cache[user.id] = time_now
                asyncio.create_task(sync_user_worker(user, chat))

        return await handler(event, data)


async def sync_user_worker(user: User, chat: Chat):
    try:
        async with get_session_local()() as session:
            repo = UserRepository(session)
            await repo.add_or_update(user.id, chat.id, user.username)
            await session.commit()
            logger.info(
                "Updated user", extra={"user_id": user.id, "username": user.username}
            )
    except SQLAlchemyError:
        logger.exception(
            "Failed to upsert user",
            extra={
                "user_id": user.id,
                "chat_id": chat.id,
            },
        )
