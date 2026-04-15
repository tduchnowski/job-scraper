from aiogram.types import Message

from jobscraper.bot.messages import get_subscriptions_text
from jobscraper.storage.repository import UserSubscriptionRepository
from jobscraper.storage.session import get_session_local


async def mysubscriptions_cmd(message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    # get subscriptions from db
    async with get_session_local()() as session:
        repo = UserSubscriptionRepository(session)
        subscriptions = await repo.get_user_subscriptions(user_id)

    await message.answer(get_subscriptions_text(subscriptions), parse_mode="markdown")
