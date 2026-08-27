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


# TODO: make one function out of the following three, its basically the same thing
def user_activity_worker(host: str, port: str, workers_group: str):
    user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
    handler = UserActivityHandler(get_session_local())
    return worker(host, port, user_activity_topic, workers_group, handler)


def subscription_worker(host: str, port: str, workers_group: str):
    subscription_topic = os.getenv("REDIS_SUBSCRIPTIONS_TOPIC", "")
    handler = SubscriptionHandler(get_session_local())
    return worker(host, port, subscription_topic, workers_group, handler)


def notification_status_worker(host: str, port: str, workers_group: str):
    notification_topic = os.getenv("REDIS_NOTIFICATION_STATUS_TOPIC", "")
    handler = NotificationStatusHandler(get_session_local())
    return worker(host, port, notification_topic, workers_group, handler)


def notifications_worker(host: str, port: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_NOTIFICATIONS_TOPIC", "")
    handler = NewNotificationHandler(get_session_local())
    return worker(host, port, new_notification_topic, workers_group, handler)


def new_job_worker(host: str, port: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_NEW_JOBS_TOPIC", "")
    handler = NewJobHandler(get_session_local())
    return worker(host, port, new_notification_topic, workers_group, handler)


def job_status_worker(host: str, port: str, workers_group: str):
    new_notification_topic = os.getenv("REDIS_JOB_STATUS_TOPIC", "")
    handler = JobStatusHandler(get_session_local())
    return worker(host, port, new_notification_topic, workers_group, handler)


async def main():
    # create redis consumers
    set_session_local()
    for key, val in os.environ.items():
        print(key, val)
    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    workers_group = os.getenv("REDIS_TELEGRAM_WORKERS_GROUP_NAME", "")
    workers = [
        asyncio.create_task(subscription_worker(redis_host, redis_port, workers_group)),
        asyncio.create_task(
            user_activity_worker(redis_host, redis_port, workers_group)
        ),
        asyncio.create_task(
            notification_status_worker(redis_host, redis_port, workers_group)
        ),
        asyncio.create_task(
            notifications_worker(redis_host, redis_port, workers_group)
        ),
        asyncio.create_task(new_job_worker(redis_host, redis_port, workers_group)),
        asyncio.create_task(job_status_worker(redis_host, redis_port, workers_group)),
    ]
    await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
