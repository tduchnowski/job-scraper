import os
from aiogram import Bot
from loguru import logger


def create_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    # webhook_url = os.environ.get("TELEGRAM_WEBHOOK")
    # if not webhook_url:
    #     logger.error("PUBLIC_URL not set, webhook not configured")
    #     raise ValueError("TELEGRAM_WEBHOOK is required")
    #
    bot = Bot(token=token)
    # await bot.set_webhook(
    #     url=webhook_url,
    #     drop_pending_updates=True,
    #     allowed_updates=["message"]
    # )
    return bot
