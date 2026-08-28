from aiogram.types import Message
from services.bot.src.messages import are_args_valid
from services.bot.src.subscription_service import SubscriptionService
from services.shared.models.queue_message import SubscribeOperation


async def unsubscribe_cmd(message: Message, subs_service: SubscriptionService):
    """Handle /unsubscribe command."""
    if not message.text or not message.from_user or not message.chat:
        return

    args_ok, error_msg = are_args_valid(message.text)
    if not args_ok:
        await message.answer(error_msg, parse_mode="markdown")
        return
    _, category, location = message.text.split()
    category, location = category.upper(), location.upper()

    success = await subs_service.update(
        message.from_user.id,
        message.chat.id,
        category,
        location,
        SubscribeOperation.REMOVE,
    )
    if not success:
        response_text = "❌ Failed to remove subscription. Please try again later"
        await message.answer(response_text, parse_mode="markdown")
    # user will be notified later when the update reaches storage


# def format_response(
#     remove_subscription_result: RemoveSubscriptionResult, category: str, location: str
# ) -> str:
#     """Format removal result into user-facing markdown message."""
#     if remove_subscription_result == RemoveSubscriptionResult.REMOVED:
#         return f"✅ You won't receive notifications for {category} -> {location}"
#     elif remove_subscription_result == RemoveSubscriptionResult.NOT_EXIST:
#         return f"✅ You're already not subscribed to {category} -> {location}"
#     else:
#         return "❌ Failed to remove subscription. Please try again later"
