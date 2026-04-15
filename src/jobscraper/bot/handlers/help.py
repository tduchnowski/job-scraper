from aiogram.types import Message

from jobscraper.bot.messages import get_help_text


async def help_cmd(message: Message):
    await message.answer(get_help_text(), parse_mode="markdown")
