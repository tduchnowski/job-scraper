from aiogram import Dispatcher
from aiogram.filters import Command

from jobscraper.bot.handlers.start import start_cmd
from jobscraper.bot.handlers.subscribe import subscribe_cmd


def register_handlers(dp: Dispatcher):
    dp.message.register(start_cmd, Command("start"))
    dp.message.register(subscribe_cmd, Command("subscribe"))
