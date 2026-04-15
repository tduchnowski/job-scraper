from aiogram.types import Message

from jobscraper.bot.messages import are_args_valid
from jobscraper.storage.repository import UserSubscriptionRepository
from jobscraper.storage.session import get_session_local


async def unsubscribe_cmd(message: Message):
    if not message.text:
        return

    args_ok, error_msg = are_args_valid(message.text)
    if not args_ok:
        await message.answer(error_msg, parse_mode="markdown")
    _, category, location = message.text.split()
    category, location = category.upper(), location.upper()

    async with get_session_local()() as session:
        if not message.from_user:
            return

        repo = UserSubscriptionRepository(session)
        sub = await repo.find_subscription(message.from_user.id, category, location)
        if not sub:
            await message.answer(
                f"✅ You're already not subscribed to {category} -> {location}"
            )
        else:
            sub.is_active = False
            await session.commit()
            await message.answer(
                f"✅ You won't receive notifications for {category} -> {location}"
            )
