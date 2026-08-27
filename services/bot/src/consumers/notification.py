from aiogram import Bot, Dispatcher
from services.shared.models.queue_message import Payload
from redisaq import Message


class UserMessageProcessor:
    def __init__(self, bot: Bot, dispatcher: Dispatcher):
        self.bot = bot
        self.dispatcher = dispatcher

    async def process(self, message: Message):
        payload = Payload.model_validate(message.payload)
        await self.bot.send_message(chat_id=payload.chat_id, text=payload.message)
