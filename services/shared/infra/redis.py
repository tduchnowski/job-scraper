import os
from redisaq import Producer, Consumer


def create_producer(host: str, port: str, topic: str, maxlen: int = 1000) -> Producer:
    if not (host and port and topic):
        raise ValueError(
            f"Can't create a queue producer. host={host}, port={port}, topic={topic}"
        )

    env = os.getenv("ENVIRONMENT", "env")
    if env == "env":
        url = f"redis://{host}:{port}/0"
        producer = Producer(topic=topic, maxlen=maxlen, redis_url=url)
    else:
        # TODO: make it different for prod env
        url = f"redis://{host}:{port}/0"
        producer = Producer(topic=topic, maxlen=maxlen, redis_url=url)

    return producer


def create_consumer(
    host: str,
    port: str,
    topic: str,
    group_name: str,
    batch_size: int = 10,
    heartbeat_interval: float = 3.0,
) -> Consumer:
    if not (host and port and topic and group_name):
        raise ValueError(
            f"Missing Redis environment variables. host={host}, port={port}, topic={topic}, group_name={group_name}"
        )

    env = os.getenv("ENVIRONMENT", "env")
    if env == "env":
        url = f"redis://{host}:{port}/0"
        consumer = Consumer(
            topic=topic,
            group_name=group_name,
            batch_size=batch_size,
            heartbeat_interval=heartbeat_interval,
            redis_url=url,
        )
    else:
        # change this later to actual prod Redis
        url = f"redis://{host}:{port}/0"
        consumer = Consumer(
            topic=topic,
            group_name=group_name,
            batch_size=batch_size,
            heartbeat_interval=heartbeat_interval,
            redis_url=url,
        )

    return consumer
