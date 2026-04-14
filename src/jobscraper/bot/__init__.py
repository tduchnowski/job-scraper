import os
from aiogram import Bot, Dispatcher
from typing import Tuple


def init_bot_and_dispatcher() -> Tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher together."""
    from jobscraper.bot.handlers import register_handlers

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    bot = Bot(token=token)
    dp = Dispatcher()
    register_handlers(dp)

    return bot, dp
