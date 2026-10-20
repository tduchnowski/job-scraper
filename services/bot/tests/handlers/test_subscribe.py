import pytest
from unittest.mock import AsyncMock, patch

from services.bot.src.handlers.subscribe import subscribe_cmd
from services.shared.models.queue_message import SubscribeOperation


@pytest.mark.asyncio
async def test_wrong_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe notenoughargs"
    message.from_user.id = 1
    with patch(
        "services.bot.src.handlers.subscribe.are_args_valid",
        return_value=(False, "error"),
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    message.answer.assert_called_once_with("error", parse_mode="markdown")
    subs_service.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_subsciption_service_fail():
    """Test good arguments but subscription service returning False"""
    message, subs_service = AsyncMock(), AsyncMock()
    subs_service.update.return_value = False
    message.text = "/subscribe Python Poland"
    message.from_user.id = 1
    with patch(
        "services.bot.src.handlers.subscribe.are_args_valid", return_value=(True, "")
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    message.answer.assert_called_once_with(
        "❌ Failed to create subscription. Please try again later",
        parse_mode="markdown",
    )
    subs_service.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_good_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe country location"
    message.from_user.id = 1
    message.chat.id = 2
    subs_service.update.return_value = True
    with patch(
        "services.bot.src.handlers.subscribe.are_args_valid", return_value=(True, "")
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    subs_service.update.assert_called_once_with(
        1, 2, "COUNTRY", "LOCATION", SubscribeOperation.ADD
    )
