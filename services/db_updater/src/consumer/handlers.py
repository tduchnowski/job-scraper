from abc import ABC, abstractmethod
from redisaq import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from services.db_updater.src.storage.models import UserORM
from services.shared.models.queue_message import (
    # NotificationUpdate,
    # SubscriptionUpdate,
    UserActivity,
)


class ConsumerHandler(ABC):
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    @abstractmethod
    async def process(self, message: Message):
        pass


class UserActivityHandler(ConsumerHandler):
    async def process(self, message: Message):
        user_activity = UserActivity.model_validate(message.payload)
        async with self.session_maker() as session:
            user = UserORM(
                id=user_activity.user_id,
                chat_id=user_activity.chat_id,
                last_interaction=user_activity.activity_time,
            )
            await session.merge(user)
            await session.commit()


# class SubscriptionHandler(ConsumerHandler):
#     async def process(self, message: Message):
#         subscription = SubscriptionUpdate.model_validate(message.payload)
#         async with self.session_maker() as session:
#             print("session works")
#
#
# class NotificationHandler(ConsumerHandler):
#     async def process(self, message: Message):
#         notification = NotificationUpdate.model_validate(message.payload)
#         async with self.session_maker() as session:
#             print(session)
