import datetime
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Chat, Message, Update
import pytest
from unittest.mock import AsyncMock, patch


from jobscraper.bot.handlers.errors import error_handler


@pytest.mark.asyncio
async def test_error_handler_gets_called():
    async def broken_handler(message: Message):
        raise Exception()

    bot = AsyncMock()
    dp = Dispatcher()
    dp.message.register(broken_handler, Command("broken"))
    dp.errors.register(error_handler)

    message = Message(
        message_id=1,
        date=datetime.datetime.now(datetime.timezone.utc),
        chat=Chat(id=2, type="private"),
        text="/broken",
    )
    message._bot = bot
    update = Update(message=message, update_id=2)
    with patch.object(Message, "answer", new=AsyncMock()) as mock_answer:
        await dp.feed_update(bot, update=update)
        mock_answer.assert_awaited_once_with(
            "Something went wrong. Please try again later"
        )


@pytest.mark.asyncio
async def test_error_handler_not_called():
    async def good_handler(message: Message):
        return

    bot = AsyncMock()
    dp = Dispatcher()
    dp.message.register(good_handler, Command("good"))
    dp.errors.register(error_handler)

    message = Message(
        message_id=1,
        date=datetime.datetime.now(datetime.timezone.utc),
        chat=Chat(id=2, type="private"),
        text="/good",
    )
    message._bot = bot
    update = Update(message=message, update_id=2)
    with patch.object(Message, "answer", new=AsyncMock()) as mock_answer:
        await dp.feed_update(bot, update=update)
        mock_answer.assert_not_awaited()
