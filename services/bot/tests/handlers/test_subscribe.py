import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.handlers.subscribe import subscribe_cmd
from jobscraper.bot.subscription_service import SubscriptionResult


@pytest.mark.asyncio
async def test_wrong_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe notenoughargs"
    message.from_user.id = 1
    with patch(
        "jobscraper.bot.handlers.subscribe.are_args_valid",
        return_value=(False, "error"),
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    message.answer.assert_called_once_with("error", parse_mode="markdown")
    subs_service.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_good_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe country location"
    message.from_user.id = 1
    subs_service.subscribe.return_value = SubscriptionResult.CREATED
    with patch(
        "jobscraper.bot.handlers.subscribe.are_args_valid", return_value=(True, "")
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    subs_service.subscribe.assert_called_once_with(1, "COUNTRY", "LOCATION")


@pytest.mark.asyncio
async def test_subscribe_exists():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe country location"
    message.from_user.id = 1
    subs_service.subscribe.return_value = SubscriptionResult.EXISTS
    with (
        patch(
            "jobscraper.bot.handlers.subscribe.format_response", return_value="exists"
        ),
        patch(
            "jobscraper.bot.handlers.subscribe.are_args_valid", return_value=(True, "")
        ),
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    message.answer.assert_called_once_with("exists", parse_mode="markdown")


@pytest.mark.asyncio
async def test_subscribe_error():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/subscribe country location"
    message.from_user.id = 1
    subs_service.subscribe.side_effect = SQLAlchemyError()
    with (
        patch("jobscraper.bot.handlers.subscribe.format_response", return_value="fail"),
        patch(
            "jobscraper.bot.handlers.subscribe.are_args_valid", return_value=(True, "")
        ),
    ):
        await subscribe_cmd(message, subs_service=subs_service)
    message.answer.assert_called_once_with("fail", parse_mode="markdown")
