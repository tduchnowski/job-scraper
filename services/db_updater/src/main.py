import os
import asyncio

import services.db_updater.src.consumer.user_activity as user_activity


async def main():
    # create redis consumers
    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    user_activity_topic = os.getenv("REDIS_USER_ACTIVITY_TOPIC", "")
    user_activity_group = os.getenv("REDIS_USER_ACTIVITY_GROUP_NAME", "")
    # subscription_topic = os.getenv("REDIS_SUBSCRIPTION_TOPIC", "")
    workers = [
        asyncio.create_task(
            user_activity.worker(
                redis_host, redis_port, user_activity_topic, user_activity_group
            )
        )
    ]
    await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(main())
