from aiogram.types import Message
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.messages import are_args_valid
from jobscraper.storage.repository import UserSubscriptionRepository
from enum import Enum


class SubscriptionResult(Enum):
    CREATED = 1
    EXISTS = 2
    FAILED = 3


class SubscribeService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def subscribe(
        self, user_id: int, category: str, location: str
    ) -> SubscriptionResult:
        res = SubscriptionResult.FAILED
        async with self.session_factory() as session:
            subs_repo = UserSubscriptionRepository(session)
            res = await self.create_subscription(subs_repo, user_id, category, location)
            await session.commit()
            return res

    async def create_subscription(
        self,
        subscription_repo: UserSubscriptionRepository,
        user_id: int,
        category: str,
        location: str,
    ) -> SubscriptionResult:
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


async def subscribe_cmd(message: Message, subs_service: SubscribeService):
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
        subscription_res = await subs_service.subscribe(
            message.from_user.id, category, location
        )
    except SQLAlchemyError as e:
        logger.error(f"DB session error: {e}")

    response_text = format_response(subscription_res, category, location)
    await message.answer(response_text, parse_mode="markdown")


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
