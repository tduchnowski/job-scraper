from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.handlers.unsubscribe import unsubscribe_cmd
from jobscraper.bot.subscription_service import RemoveSubscriptionResult


@pytest.mark.asyncio
async def test_unsubscribe_wrong_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/unsubscribe onlyonearg"
    message.from_user.id = 1

    with patch(
        "jobscraper.bot.handlers.unsubscribe.are_args_valid",
        return_value=(False, "error"),
    ):
        await unsubscribe_cmd(message, subs_service=subs_service)

    message.answer.assert_called_once_with("error", parse_mode="markdown")
    subs_service.unsubscribe.assert_not_called()


@pytest.mark.asyncio
async def test_unsubscribe_removed():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/unsubscribe country location"
    message.from_user.id = 1

    subs_service.unsubscribe.return_value = RemoveSubscriptionResult.REMOVED

    with (
        patch(
            "jobscraper.bot.handlers.unsubscribe.format_response",
            return_value="removed",
        ),
        patch(
            "jobscraper.bot.handlers.unsubscribe.are_args_valid",
            return_value=(True, ""),
        ),
    ):
        await unsubscribe_cmd(message, subs_service=subs_service)

    subs_service.unsubscribe.assert_called_once()
    message.answer.assert_called_once_with("removed", parse_mode="markdown")


@pytest.mark.asyncio
async def test_unsubscribe_not_exist():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/unsubscribe country location"
    message.from_user.id = 1

    subs_service.unsubscribe.return_value = RemoveSubscriptionResult.NOT_EXIST

    with (
        patch(
            "jobscraper.bot.handlers.unsubscribe.format_response",
            return_value="not_exist",
        ),
        patch(
            "jobscraper.bot.handlers.unsubscribe.are_args_valid",
            return_value=(True, ""),
        ),
    ):
        await unsubscribe_cmd(message, subs_service=subs_service)

    message.answer.assert_called_once_with("not_exist", parse_mode="markdown")


@pytest.mark.asyncio
async def test_unsubscribe_db_error():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/unsubscribe country location"
    message.from_user.id = 1

    subs_service.unsubscribe.side_effect = SQLAlchemyError()

    with (
        patch(
            "jobscraper.bot.handlers.unsubscribe.format_response",
            return_value="fail",
        ),
        patch(
            "jobscraper.bot.handlers.unsubscribe.are_args_valid",
            return_value=(True, ""),
        ),
    ):
        await unsubscribe_cmd(message, subs_service=subs_service)

    message.answer.assert_called_once_with("fail", parse_mode="markdown")
