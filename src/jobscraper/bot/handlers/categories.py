from aiogram.types import Message

from jobscraper.bot.messages import get_categories_text
from jobscraper.config.scraping_config import SEARCH_QUERIES


async def categories_cmd(message: Message):
    await message.answer(
        get_categories_text(list(SEARCH_QUERIES.keys())), parse_mode="markdown"
    )
