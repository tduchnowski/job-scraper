from abc import ABC, abstractmethod
from redisaq import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from services.db_updater.src.storage.models import (
    JobORM,
    NotificationORM,
    UserORM,
    UserSubscriptionORM,
)
from services.shared.models.queue_message import (
    JobUpdate,
    NewJob,
    NewNotification,
    NotificationUpdate,
    SubscriptionUpdate,
    UserActivity,
    SubscribeOperation,
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


class SubscriptionHandler(ConsumerHandler):
    async def process(self, message: Message):
        subscription = SubscriptionUpdate.model_validate(message.payload)
        async with self.session_maker() as session:
            stmt = select(UserSubscriptionORM).where(
                UserSubscriptionORM.user_id == subscription.user_id,
                UserSubscriptionORM.category == subscription.category,
                UserSubscriptionORM.location == subscription.location,
            )
            subscription_orm = (await session.execute(stmt)).scalar_one_or_none()
            if (
                subscription_orm is None
                and subscription.operation == SubscribeOperation.ADD
            ):
                subscription_orm = UserSubscriptionORM(
                    user_id=subscription.user_id,
                    category=subscription.category,
                    location=subscription.location,
                )
            elif subscription_orm is not None:
                if subscription.operation == SubscribeOperation.REMOVE:
                    subscription_orm.is_active = False
                elif subscription.operation == SubscribeOperation.ADD:
                    subscription_orm.is_active = True
            await session.merge(subscription_orm)
            await session.commit()
            # send a message confirming success or failure of this operation


class NotificationStatusHandler(ConsumerHandler):
    async def process(self, message: Message):
        notification_status = NotificationUpdate.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            notification_orm = NotificationORM(
                id=notification_status.notification_id,
                status=notification_status.status,
            )
            await session.merge(notification_orm)
            await session.commit()


class NewNotificationHandler(ConsumerHandler):
    async def process(self, message: Message):
        notification = NewNotification.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            notification_orm = NotificationORM(
                user_id=notification.user_id,
                job_id=notification.job_id,
                subscription_id=notification.subscription_id,
            )
            await session.merge(notification_orm)
            await session.commit()


class JobStatusHandler(ConsumerHandler):
    async def process(self, message: Message):
        job_status = JobUpdate.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            job_orm = JobORM(job_id=job_status.job_id, status=job_status.status)
            await session.merge(job_orm)
            await session.commit()


class NewJobHandler(ConsumerHandler):
    async def process(self, message: Message):
        job = NewJob.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            job_orm = JobORM(
                url=job.url,
                title=job.title,
                company=job.company,
                category=job.category,
                location=job.location,
                scraped_at=job.scraped_at,
            )
            await session.merge(job_orm)
            await session.commit()
