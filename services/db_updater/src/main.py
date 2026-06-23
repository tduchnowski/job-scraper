import os
import asyncio


from services.db_updater.src.consumer.handlers import (
    process_user_activity,
    process_subscription,
)
from services.db_updater.src.consumer.worker import worker


def user_activity_worker(host: str, port: str):
    user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
    user_activity_group = os.getenv("REDIS_USER_ACTIVITY_GROUP_NAME", "")
    return worker(
        host, port, user_activity_topic, user_activity_group, process_user_activity
    )


def subscription_worker(host: str, port: str):
    subscription_topic = os.getenv("REDIS_SUBSCRIPTION_TOPIC", "")
    subscription_group = os.getenv("REDIS_SUBSCRIPTION_GROUP_NAME", "")
    return worker(
        host, port, subscription_topic, subscription_group, process_subscription
    )


async def main():
    # create redis consumers
    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    workers = [
        asyncio.create_task(user_activity_worker(redis_host, redis_port)),
        asyncio.create_task(subscription_worker(redis_host, redis_port)),
    ]
    await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
