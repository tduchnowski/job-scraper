from aiogram.types import Message
from services.bot.src.subscription_service import SubscriptionService
from services.bot.src.messages import are_args_valid
from services.shared.models.queue_message import SubscribeOperation


async def subscribe_cmd(message: Message, subs_service: SubscriptionService):
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
        SubscribeOperation.ADD,
    )
    if not success:
        response_text = "❌ Failed to create subscription. Please try again later"
        await message.answer(response_text, parse_mode="markdown")
    # user will be notified by other means when the subscription is successfully stored


# def format_response(
#     subscription_result: SubscriptionResult, category: str, location: str
# ):
#     """Format subscription result into user-facing markdown message."""
#     if subscription_result == SubscriptionResult.CREATED:
#         return (
#             f"✅ Subscribed to `{category}` jobs in `{location}`!\n\n"
#             f"You'll receive notifications for new matching jobs.\n"
#             f"Use `/unsubscribe {category} {location}` to stop.\n\n"
#             "Use /mysubscriptions to view your current subscriptions"
#         )
#     elif subscription_result == SubscriptionResult.EXISTS:
#         return f"ℹ️ You're already subscribed to `{category}` jobs in `{location}`\n\n"
#     else:
#         return "❌ Failed to create subscription. Please try again later"
