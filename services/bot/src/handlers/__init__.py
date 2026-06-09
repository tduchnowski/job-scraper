from aiogram import Dispatcher
from aiogram.filters import Command

from .categories import categories_cmd
from .errors import error_handler
from .help import help_cmd
from .list_subscriptions import mysubscriptions_cmd
from .start import start_cmd
from .subscribe import subscribe_cmd
from .unsubscribe import unsubscribe_cmd
# from subscription_service import SubscriptionService
# from jobscraper.storage.session import get_session_local


def register_handlers(dp: Dispatcher):
    # commands
    dp.message.register(start_cmd, Command("start"))
    # subs_service = SubscriptionService(get_session_local())
    # dp["subs_service"] = subs_service
    dp.message.register(subscribe_cmd, Command("subscribe"))
    dp.message.register(unsubscribe_cmd, Command("unsubscribe"))
    dp.message.register(mysubscriptions_cmd, Command("mysubscriptions"))
    dp.message.register(categories_cmd, Command("categories"))
    dp.message.register(help_cmd, Command("help"))

    # errors
    dp.errors.register(error_handler)
