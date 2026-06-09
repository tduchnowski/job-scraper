import os
from redisaq import Producer


def create_producer(maxlen: int = 1000) -> Producer:
    host = os.getenv("REDIS_HOST")
    port = os.getenv("REDIS_PORT")
    topic = os.getenv("REDIS_QUEUE_USER_UPDATE_TOPIC")
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
