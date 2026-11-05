from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from loguru import logger
from pydantic import ValidationError
from redisaq import Message, Producer

from services.shared.models.queue_message import (
    NotificationStatus,
    NotificationUpdate,
    TelegramUserMessage,
    UserActivity,
)


class UserMessageProcessor:
    def __init__(
        self,
        bot: Bot,
        notification_status_producer: Producer,
        user_activity_producer: Producer,
    ):
        self.bot = bot
        self.notification_status_producer = notification_status_producer
        self.user_activity_producer = user_activity_producer

    # TODO: there are still more exceptions that can be handled here
    async def process(self, message: Message):
        try:
            message_for_user = TelegramUserMessage.model_validate(message.payload)
        except ValidationError:
            logger.error(
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
        except TelegramForbiddenError:
            logger.warning(
                "Bot blocked. Invalidating the user...",
                extra={
                    "chat_id": message_for_user.chat_id,
                    "username": message_for_user.username,
                },
            )
            await self._emit_user_invalidation(message_for_user)
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

    async def _emit_user_invalidation(self, msg: TelegramUserMessage):
        try:
            user_activity = UserActivity(
                user_id=msg.user_id,
                chat_id=msg.chat_id,
                username=msg.username,
                is_active=False,
            ).model_dump(mode="json")
            await self.user_activity_producer.enqueue(user_activity)
        except Exception:
            logger.exception(
                "Failed to send invalidation user activity",
                extra={"user_activity_raw": user_activity},
            )
