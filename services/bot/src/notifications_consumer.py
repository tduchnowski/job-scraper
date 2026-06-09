import os
from aiogram import Bot, Dispatcher
from services.shared.models.queue_message import Payload
from redisaq import Consumer, Message


class MessageProcessor:
    def __init__(self, bot: Bot, dispatcher: Dispatcher):
        self.bot = bot
        self.dispatcher = dispatcher

    async def process(self, message: Message):
        payload = Payload.model_validate(message.payload)
        await self.bot.send_message(chat_id=payload.chat_id, text=payload.message)


def create_consumer(batch_size: int = 10, heartbeat_interval: float = 3.0) -> Consumer:
    host = os.getenv("REDIS_HOST")
    port = os.getenv("REDIS_PORT")
    topic = os.getenv("REDIS_QUEUE_NOTIFICATIONS_TOPIC")
    group_name = os.getenv("REDIS_QUEUE_NOTIFICATIONS_GROUP_NAME")

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
