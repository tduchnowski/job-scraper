from datetime import datetime, timezone
from aiogram.types import Message
from loguru import logger
from jobscraper.storage.models import UserORM
from jobscraper.storage.session import SessionLocal


async def start_cmd(message: Message):
    # Save user to database
    async with SessionLocal() as session:
        # Check if user exists
        if not message.from_user:
            return
        user = await session.get(UserORM, message.from_user.id)

        if not user:
            # Create new user
            user = UserORM(
                id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                created_at=datetime.now(timezone.utc),
                last_interaction=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()
            logger.info(f"New user saved: {user.id} ({user.username})")
        else:
            # Update last interaction
            user.last_interaction = datetime.now(timezone.utc)
            await session.commit()
            logger.debug(f"User updated: {user.id}")

    await message.answer(
        "Hi! Welcome to Job Notifier Bot. Use /subscribe to get job notifications."
    )
