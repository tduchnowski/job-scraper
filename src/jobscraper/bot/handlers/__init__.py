from aiogram import Dispatcher
from aiogram.filters import Command

from jobscraper.bot.handlers.categories import categories_cmd
from jobscraper.bot.handlers.errors import error_handler
from jobscraper.bot.handlers.help import help_cmd
from jobscraper.bot.handlers.list_subscriptions import mysubscriptions_cmd
from jobscraper.bot.handlers.start import start_cmd
from jobscraper.bot.handlers.subscribe import SubscribeService, subscribe_cmd
from jobscraper.bot.handlers.unsubscribe import unsubscribe_cmd
from jobscraper.storage.session import get_session_local


def register_handlers(dp: Dispatcher):
    # commands
    dp.message.register(start_cmd, Command("start"))
    subs_service = SubscribeService(get_session_local())
    dp["subs_service"] = subs_service
    dp.message.register(subscribe_cmd, Command("subscribe"))
    dp.message.register(unsubscribe_cmd, Command("unsubscribe"))
    dp.message.register(mysubscriptions_cmd, Command("mysubscriptions"))
    dp.message.register(categories_cmd, Command("categories"))
    dp.message.register(help_cmd, Command("help"))

    # errors
    dp.errors.register(error_handler)
