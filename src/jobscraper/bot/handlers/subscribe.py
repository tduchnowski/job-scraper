from aiogram.types import Message
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from jobscraper.bot.messages import are_args_valid
from jobscraper.storage.repository import UserSubscriptionRepository
from jobscraper.storage.session import get_session_local
from enum import Enum


class SubscriptionResult(Enum):
    CREATED = 1
    EXISTS = 2
    FAILED = 3


def format_response(
    subscription_result: SubscriptionResult, category: str, location: str
):
    if subscription_result == SubscriptionResult.CREATED:
        return (
            f"✅ Subscribed to `{category}` jobs in `{location}`!\n\n"
            f"You'll receive notifications for new matching jobs.\n"
            f"Use `/unsubscribe {category} {location}` to stop.\n\n"
            "Use /mysubscriptions to view your current subscriptions"
        )
    elif subscription_result == SubscriptionResult.EXISTS:
        return f"ℹ️ You're already subscribed to `{category}` jobs in `{location}`\n\n"
    else:
        return "❌ Failed to create subscription. Please try again later"


async def subscribe_cmd(message: Message):
    """Handle /subscribe category location command."""
    if not message.text or not message.from_user:
        return

    args_ok, error_msg = are_args_valid(message.text)
    if not args_ok:
        await message.answer(error_msg, parse_mode="markdown")
        return
    _, category, location = message.text.split()
    category, location = category.upper(), location.upper()

    subscription_res = SubscriptionResult.FAILED
    try:
        async with get_session_local()() as session:
            subscription_res = await create_subscription_response(
                session, message.from_user.id, category, location
            )
            await session.commit()
    except SQLAlchemyError as e:
        logger.error(f"DB session error: {e}")

    response_text = format_response(subscription_res, category, location)
    await message.answer(response_text, parse_mode="markdown")


async def create_subscription_response(
    session: AsyncSession, user_id: int, category: str, location: str
) -> SubscriptionResult:
    subscription_repo = UserSubscriptionRepository(session)

    try:
        existing = await subscription_repo.find_subscription(
            user_id, category, location
        )
        if existing:
            return SubscriptionResult.EXISTS
        await subscription_repo.create_subscription(user_id, category, location)
        return SubscriptionResult.CREATED
    except SQLAlchemyError as e:
        logger.error(f"DB error while creating subscription: {e}")
        return SubscriptionResult.FAILED
