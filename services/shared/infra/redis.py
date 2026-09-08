from redisaq import Producer, Consumer


def create_producer(redis_url: str, topic: str, maxlen: int = 1000) -> Producer:
    if not (redis_url and topic):
        raise ValueError(
            f"Can't create a queue producer. redis_url={redis_url}, topic={topic}"
        )
    producer = Producer(topic=topic, maxlen=maxlen, redis_url=redis_url)
    return producer


def create_consumer(
    redis_url: str,
    topic: str,
    group_name: str,
    batch_size: int = 10,
    heartbeat_interval: float = 3.0,
) -> Consumer:
    if not (redis_url and topic and group_name):
        raise ValueError(
            f"Missing Redis environment variables. redis_url={redis_url}, topic={topic}, group_name={group_name}"
        )
    consumer = Consumer(
        topic=topic,
        group_name=group_name,
        batch_size=batch_size,
        heartbeat_interval=heartbeat_interval,
        redis_url=redis_url,
    )
    return consumer
