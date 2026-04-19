from typing import Sequence
from aiogram.types import Message
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.storage.models import UserSubscriptionORM
from jobscraper.storage.repository import UserSubscriptionRepository
from jobscraper.storage.session import get_session_local


async def mysubscriptions_cmd(message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    # get subscriptions from db
    subscriptions = []
    try:
        async with get_session_local()() as session:
            repo = UserSubscriptionRepository(session)
            subscriptions = await repo.get_user_subscriptions(user_id)
    except SQLAlchemyError as e:
        logger.error(f"DB session error: {e}")
        await message.answer("Something went wrong. Please try again later")

    await message.answer(
        format_subscriptions_list(subscriptions), parse_mode="markdown"
    )


def format_subscriptions_list(subscriptions: Sequence[UserSubscriptionORM]) -> str:
    """Convert subscriptions to markdown list with usage instructions."""
    if not subscriptions:
        return (
            "📋 *You have no active subscriptions*\n\n"
            "💡 *Get started:*\n"
            "Use `/subscribe <CATEGORY> <LOCATION>` to start receiving job notifications\n\n"
            "Use `/categories` to see all available categories"
        )

    sorted_subs = sorted(subscriptions, key=lambda s: (s.category, s.location))
    subscription_lines = []
    for i, sub in enumerate(sorted_subs, 1):
        subscription_lines.append(f"{i}. {sub.category.value} → {sub.location}")

    subscriptions_list = "\n".join(subscription_lines)
    return (
        "📋 *Your Active Subscriptions*\n\n"
        f"{subscriptions_list}\n\n"
        "❌ *Remove a subscription:*\n"
        "Use `/unsubscribe <CATEGORY> <LOCATION>`\n\n"
    )
