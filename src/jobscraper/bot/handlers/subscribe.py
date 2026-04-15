from datetime import datetime, timezone
from aiogram.types import Message
from loguru import logger
from sqlalchemy import and_, select

from jobscraper.bot.messages import are_args_valid
from jobscraper.storage.models import UserORM, UserSubscriptionORM
from jobscraper.storage.session import get_session_local


async def subscribe_cmd(message: Message):
    """Handle /subscribe category location command."""
    if not message.text:
        return

    args_ok, error_msg = are_args_valid(message.text)
    if not args_ok:
        await message.answer(error_msg, parse_mode="markdown")
        return
    _, category, location = message.text.split()
    category, location = category.upper(), location.upper()

    # Save subscription
    async with get_session_local()() as session:
        # Check if user exists, create if not
        if not message.from_user:
            return
        user = await session.get(UserORM, message.from_user.id)
        if not user:
            user = UserORM(
                id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                created_at=datetime.now(timezone.utc),
                last_interaction=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()

        # Check if subscription already exists
        existing = await session.execute(
            select(UserSubscriptionORM).where(
                and_(
                    UserSubscriptionORM.user_id == message.from_user.id,
                    UserSubscriptionORM.category == category,
                    UserSubscriptionORM.location == location,
                )
            )
        )
        if existing.scalar_one_or_none():
            await message.answer(
                f"ℹ️ You're already subscribed to `{category}` jobs in `{location}`.\n\n",
                parse_mode="Markdown",
            )
            return

        # Create new subscription
        try:
            subscription = UserSubscriptionORM(
                user_id=message.from_user.id,
                category=category,
                location=location,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_notified_at=datetime.fromtimestamp(0, tz=timezone.utc),
            )
            session.add(subscription)
            await session.commit()

            await message.answer(
                f"✅ Subscribed to `{category}` jobs in `{location}`!\n\n"
                f"You'll receive notifications for new matching jobs.\n"
                f"Use `/unsubscribe {category} {location}` to stop.\n\n"
                "Use /mysubscriptions to view your current subscriptions",
                parse_mode="markdown",
            )
            logger.info(
                f"User {message.from_user.id} subscribed to {category}->{location}"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create subscription: {e}")
            await message.answer(
                "❌ Failed to create subscription. Please try again later.",
            )
