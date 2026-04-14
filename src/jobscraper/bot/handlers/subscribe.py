from datetime import datetime, timezone
from aiogram.types import Message
from loguru import logger
from sqlalchemy import and_, select

from jobscraper.config.scraping_config import LOCATIONS, SEARCH_QUERIES
from jobscraper.storage.models import UserORM, UserSubscriptionORM
from jobscraper.storage.session import get_session_local


async def subscribe_cmd(message: Message):
    """Handle /subscribe category location command."""
    if not message.text:
        return

    # Parse arguments
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "Usage: /subscribe <category> <location>\n\n"
            "Example: `/subscribe PYTHON Poland`",
        )
        return

    _, category, location = args
    category = category.upper()
    location = location.upper()

    # Validate category
    if category not in SEARCH_QUERIES:
        await message.answer(
            f"❌ Invalid category: `{category}`\n\n"
            "✅ Valid categories:\n"
            f"{'\n'.join(SEARCH_QUERIES.keys())}"
        )
        return

    # Validate location (basic - not empty)
    if location not in LOCATIONS:
        await message.answer(
            "❌ Please provide a valid country as a location.\n\n"
            "Examples: `Poland`, `Germany`, `Remote`, `UK`",
        )
        return

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
                f"ℹ️ You're already subscribed to `{category}` jobs in `{location}`.\n\n"
                f"Use `/unsubscribe {category} {location}` to remove.",
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
                f"Use `/unsubscribe {category} {location}` to stop.",
            )
            logger.info(
                f"User {message.from_user.id} subscribed to {category}/{location}"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create subscription: {e}")
            await message.answer(
                "❌ Failed to create subscription. Please try again later.",
            )
