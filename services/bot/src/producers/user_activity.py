import os
from redisaq import Producer


def create_user_activity_producer(
    host: str, port: str, topic: str, maxlen: int = 1000
) -> Producer:
    if not (host and port and topic):
        raise ValueError(
            f"Can't create a user update queue producer. host={host}, port={port}, topic={topic}"
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
