from redisaq import Message
from services.shared.models.queue_message import UserActivity


# async def worker(host: str, port: str, topic: str, group: str, handler):
#     if not (host and port and topic and group):
#         raise ValueError(
#             f"User activity worker fail - not all queue information was specified. host={host}, port={port}, topic={topic}, group={group}"
#         )
#
#     user_activity_consumer = create_consumer(
#         host=host, port=port, topic=topic, group_name=group
#     )
#     await user_activity_consumer.connect()
#     await user_activity_consumer.consume(handler)


async def process_message(activity_message: Message):
    user_activity = UserActivity.model_validate(activity_message.payload)
    print(user_activity)
