from enum import Enum
from aiogram.types import Message
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from jobscraper.bot.messages import are_args_valid
from jobscraper.storage.repository import UserSubscriptionRepository
from jobscraper.storage.session import get_session_local


class RemoveSubscriptionResult(Enum):
    REMOVED = 1
    NOT_EXIST = 2
    FAILED = 3


def format_response(
    remove_subscription_result: RemoveSubscriptionResult, category: str, location: str
) -> str:
    if remove_subscription_result == RemoveSubscriptionResult.REMOVED:
        return f"✅ You won't receive notifications for {category} -> {location}"
    elif remove_subscription_result == RemoveSubscriptionResult.NOT_EXIST:
        return f"✅ You're already not subscribed to {category} -> {location}"
    else:
        return "❌ Failed to remove subscription. Please try again later"


async def unsubscribe_cmd(message: Message):
    if not message.text or not message.from_user:
        return

    args_ok, error_msg = are_args_valid(message.text)
    if not args_ok:
        await message.answer(error_msg, parse_mode="markdown")
        return
    _, category, location = message.text.split()
    category, location = category.upper(), location.upper()

    result = RemoveSubscriptionResult.FAILED
    try:
        async with get_session_local()() as session:
            result = await delete_subscription(
                session, message.from_user.id, category, location
            )
            await session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Session fail: {e}")

    response_text = format_response(result, category, location)
    await message.answer(response_text, parse_mode="markdown")


async def delete_subscription(
    session: AsyncSession, user_id: int, category: str, location: str
) -> RemoveSubscriptionResult:
    repo = UserSubscriptionRepository(session)
    try:
        sub = await repo.find_subscription(user_id, category, location)
        if not sub:
            return RemoveSubscriptionResult.NOT_EXIST
        else:
            sub.is_active = False
            return (
                RemoveSubscriptionResult.REMOVED
            )  # technically its more like marking as inactive than removing...
    except SQLAlchemyError as e:
        logger.error(f"DB error while creating subscription: {e}")
        return RemoveSubscriptionResult.FAILED
