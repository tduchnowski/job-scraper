from aiogram import Bot
from pydantic import ValidationError
from services.shared.models.queue_message import (
    NotificationStatus,
    NotificationUpdate,
    TelegramUserMessage,
)
from redisaq import Message, Producer
from loguru import logger


class UserMessageProcessor:
    def __init__(self, bot: Bot, notification_status_producer: Producer):
        self.bot = bot
        self.notification_status_producer = notification_status_producer

    # TODO: there are still more exceptions that can be handled here
    async def process(self, message: Message):
        try:
            message_for_user = TelegramUserMessage.model_validate(message.payload)
        except ValidationError:
            logger.exception(
                "Dropping malformed queue message. Payload validation failed",
                extra={"raw_payload": getattr(message, "payload", None)},
            )
            return

        try:
            await self.bot.send_message(
                chat_id=message_for_user.chat_id, text=message_for_user.message
            )
            await self._emit_notification_update(
                message_for_user.notification_ids, NotificationStatus.SUCCESS
            )
        except Exception:
            # for now just log an exception and mark all notifications as fail
            logger.exception(
                "Unexpected exception when processing user message",
                extra={"raw_payload": getattr(message, "payload", None)},
            )
            await self._emit_notification_update(
                message_for_user.notification_ids, NotificationStatus.FAIL
            )

    async def _emit_notification_update(
        self, notification_ids: list[int] | None, status: NotificationStatus
    ):
        if not notification_ids:
            return
        batch = [
            NotificationUpdate(
                notification_id=notification_id, status=status
            ).model_dump(mode="json")
            for notification_id in notification_ids
        ]
        await self.notification_status_producer.batch_enqueue(batch)
