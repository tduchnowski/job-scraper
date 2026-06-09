from datetime import datetime, timedelta
from aiogram import BaseMiddleware
from redisaq import Producer

from services.shared.models.queue_message import UserUpdate


# TODO: implement a cache that has a limit for entries
class UserTrackingCache:
    pass


class UserTrackingMiddleware(BaseMiddleware):
    def __init__(self, queue_producer: Producer):
        self.queue_producer = queue_producer
        self.cache = {}  # user_id -> time

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        chat = data.get("event_chat")

        if user and chat:
            now = datetime.now()

            last_seen = self.cache.get(user.id)

            if last_seen is None or now - last_seen > timedelta(minutes=1):
                self.cache[user.id] = now
                user_update = UserUpdate(
                    user_id=user.id, chat_id=chat.id, username=user.username
                )
                await self.queue_producer.enqueue(user_update.model_dump())

        return await handler(event, data)


# async def sync_user_worker(user: User, chat: Chat):
#     try:
#         async with get_session_local()() as session:
#             repo = UserRepository(session)
#             await repo.add_or_update(user.id, chat.id, user.username)
#             await session.commit()
#             logger.info(
#                 "Updated user", extra={"user_id": user.id, "username": user.username}
#             )
#     except SQLAlchemyError:
#         logger.exception(
#             "Failed to upsert user",
#             extra={
#                 "user_id": user.id,
#                 "chat_id": chat.id,
#             },
#         )
