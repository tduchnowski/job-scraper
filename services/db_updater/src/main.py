import os
import asyncio


from services.db_updater.src.storage.session import get_session_local, set_session_local
from services.db_updater.src.consumer.handlers import (
    UserActivityHandler,
    SubscriptionHandler,
    NotificationHandler,
)
from services.db_updater.src.consumer.worker import worker


# TODO: make one function out of the following three, its basically the same thing
def user_activity_worker(host: str, port: str):
    user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
    user_activity_group = os.getenv("REDIS_USER_ACTIVITY_GROUP_NAME", "")
    user_activity_handler = UserActivityHandler(get_session_local())
    return worker(
        host, port, user_activity_topic, user_activity_group, user_activity_handler
    )


def subscription_worker(host: str, port: str):
    subscription_topic = os.getenv("REDIS_SUBSCRIPTION_TOPIC", "")
    subscription_group = os.getenv("REDIS_SUBSCRIPTION_GROUP_NAME", "")
    subscription_handler = SubscriptionHandler(get_session_local())
    return worker(
        host, port, subscription_topic, subscription_group, subscription_handler
    )


def notification_worker(host: str, port: str):
    notification_topic = os.getenv("REDIS_NOTIFICATION_TOPIC", "")
    notification_group = os.getenv("REDIS_NOTIFICATION_GROUP_NAME", "")
    notification_handler = NotificationHandler(get_session_local())
    return worker(
        host, port, notification_topic, notification_group, notification_handler
    )


async def main():
    # create redis consumers
    set_session_local()
    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    workers = [
        asyncio.create_task(user_activity_worker(redis_host, redis_port)),
        asyncio.create_task(subscription_worker(redis_host, redis_port)),
        asyncio.create_task(notification_worker(redis_host, redis_port)),
    ]
    await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
