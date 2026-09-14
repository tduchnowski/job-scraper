from services.db_updater.src.consumer.handlers import ConsumerHandler
from services.shared.infra.redis import create_consumer


async def worker(redis_url: str, topic: str, group: str, handler: ConsumerHandler):
    if not (redis_url and topic and group):
        raise ValueError(
            f"User activity worker fail - not all queue information was specified. redis_url={redis_url}, topic={topic}, group={group}"
        )

    user_activity_consumer = create_consumer(
        redis_url=redis_url, topic=topic, group_name=group
    )
    await user_activity_consumer.connect()
    await user_activity_consumer.consume(handler.process)
