import os
import asyncio


from services.db_updater.src.storage.session import get_session_local, set_session_local
from services.db_updater.src.consumer.handlers import (
    JobStatusHandler,
    NewJobHandler,
    NewNotificationHandler,
    UserActivityHandler,
    SubscriptionHandler,
    NotificationStatusHandler,
)
from services.db_updater.src.consumer.worker import worker
from services.shared.infra.redis import create_producer


def user_activity_worker(redis_url: str, workers_group: str):
    user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
    handler = UserActivityHandler(get_session_local())
    return worker(redis_url, user_activity_topic, workers_group, handler)


async def subscription_worker(redis_url: str, workers_group: str):
    subscription_topic = os.getenv("REDIS_SUBSCRIPTIONS_TOPIC", "")
    user_messages_topic = os.getenv("REDIS_USER_MESSAGES_TOPIC", "")
    telegram_message_queue_producer = create_producer(redis_url, user_messages_topic)
    await telegram_message_queue_producer.connect()
    handler = SubscriptionHandler(get_session_local(), telegram_message_queue_producer)
    return worker(redis_url, subscription_topic, workers_group, handler)


def notification_status_worker(redis_url: str, workers_group: str):
    notification_topic = os.getenv("REDIS_NOTIFICATION_STATUS_TOPIC", "")
    handler = NotificationStatusHandler(get_session_local())
    return worker(redis_url, notification_topic, workers_group, handler)


def notifications_worker(redis_url: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_NOTIFICATIONS_TOPIC", "")
    handler = NewNotificationHandler(get_session_local())
    return worker(redis_url, new_notification_topic, workers_group, handler)


def new_job_worker(redis_url: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_NEW_JOBS_TOPIC", "")
    handler = NewJobHandler(get_session_local())
    return worker(redis_url, new_notification_topic, workers_group, handler)


def job_status_worker(redis_url: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_JOB_STATUS_TOPIC", "")
    handler = JobStatusHandler(get_session_local())
    return worker(redis_url, new_notification_topic, workers_group, handler)


async def main():
    # create redis consumers
    set_session_local()
    redis_url = os.getenv("REDIS_URL", "")
    workers_group = os.getenv("REDIS_TELEGRAM_WORKERS_GROUP_NAME", "")

    workers = [
        asyncio.create_task(await subscription_worker(redis_url, workers_group)),
        asyncio.create_task(user_activity_worker(redis_url, workers_group)),
        asyncio.create_task(notification_status_worker(redis_url, workers_group)),
        asyncio.create_task(notifications_worker(redis_url, workers_group)),
        asyncio.create_task(new_job_worker(redis_url, workers_group)),
        asyncio.create_task(job_status_worker(redis_url, workers_group)),
    ]
    await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
