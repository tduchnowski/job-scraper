from abc import ABC, abstractmethod
from loguru import logger
from pydantic import ValidationError
from redisaq import Message, Producer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from services.shared.storage.models import (
    JobORM,
    NotificationORM,
    UserORM,
    UserSubscriptionORM,
)

# from services.db_updater.src.storage.models import (
#     JobORM,
#     NotificationORM,
#     UserORM,
#     UserSubscriptionORM,
# )
from services.shared.models.queue_message import (
    JobUpdate,
    NewJob,
    NewNotification,
    NotificationUpdate,
    Payload,
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
    def __init__(self, session_maker, telegram_message_queue: Producer):
        self.session_maker = session_maker
        self.telegram_message_queue = telegram_message_queue

    async def process(self, message: Message):
        ack_message = ""
        try:
            subscription = SubscriptionUpdate.model_validate(message.payload)
        except ValidationError as e:
            logger.error(f"Inbound message failed schema validation: {e.json()}")
            return
        except Exception as e:
            logger.exception(e)
            return

        try:
            async with self.session_maker() as session:
                try:
                    stmt = select(UserSubscriptionORM).where(
                        UserSubscriptionORM.user_id == subscription.user_id,
                        UserSubscriptionORM.category == subscription.category,
                        UserSubscriptionORM.location == subscription.location,
                    )
                    subscription_orm = (
                        await session.execute(stmt)
                    ).scalar_one_or_none()
                    ack_message = self._make_ack_message(subscription, subscription_orm)
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
                except SQLAlchemyError:
                    raise
        except (SQLAlchemyError, Exception) as e:
            logger.exception("Subscription update failure", e)
            ack_message = "Something went wrong. Try again later"

        await self.telegram_message_queue.enqueue(
            Payload(chat_id=subscription.chat_id, message=ack_message).model_dump(
                mode="json"
            )
        )

    def _make_ack_message(
        self,
        subscription: SubscriptionUpdate,
        current_subscription: UserSubscriptionORM | None,
    ) -> str:
        logger.info(subscription)
        if current_subscription:
            logger.info(
                f"current subscription. is active? -> {current_subscription.is_active}"
            )
        else:
            logger.info("no subscription here")
        if current_subscription is None:
            if subscription.operation == SubscribeOperation.ADD:
                return f"You will now receive notifications about {subscription.category} jobs in {subscription.location}"
            else:
                return f"You were already not subscribed to {subscription.category} jobs in {subscription.location}"
        else:
            if current_subscription.is_active:
                if subscription.operation == SubscribeOperation.REMOVE:
                    return f"You will no longer receive notifications about {subscription.category} jobs in {subscription.location}"
                else:
                    return f"You are already subscribed to {subscription.category} jobs in {subscription.location}. I will keep sending you notifications about those jobs"
            else:
                if subscription.operation == SubscribeOperation.ADD:
                    return f"You will now receive notifications about {subscription.category} jobs in {subscription.location}"
                else:
                    return f"You were already not subscribed to {subscription.category} jobs in {subscription.location}"


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
            try:
                notification_orm = NotificationORM(
                    user_id=notification.user_id,
                    job_id=notification.job_id,
                    subscription_id=notification.subscription_id,
                )
                await session.merge(notification_orm)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info(
                    f"Duplicate notification. Skipping. (user_id, job_id)=({notification.user_id}, {notification.job_id})"
                )


class JobStatusHandler(ConsumerHandler):
    async def process(self, message: Message):
        job_status = JobUpdate.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            job_orm = JobORM(id=job_status.job_id, status=job_status.status)
            await session.merge(job_orm)
            await session.commit()


class NewJobHandler(ConsumerHandler):
    async def process(self, message: Message):
        job = NewJob.model_validate(message.payload)
        async with self.session_maker() as session:
            # TODO: add exception handling
            job_orm = JobORM(
                id=job.id,
                url=job.url,
                title=job.title,
                company=job.company,
                category=job.category,
                location=job.location,
                scraped_at=job.scraped_at,
            )
            await session.merge(job_orm)
            await session.commit()
