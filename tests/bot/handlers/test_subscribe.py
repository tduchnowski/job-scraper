import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.handlers.subscribe import (
    SubscriptionResult,
    SubscribeService,
    subscribe_cmd,
)


# --- SubscriptionService.create_subscription tests


@pytest.mark.asyncio
async def test_subscription_exists():
    repo = AsyncMock()
    repo.find_subscription.return_value = object()
    subs_service = SubscribeService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.EXISTS
    repo.create_subscription.assert_not_called()


@pytest.mark.asyncio
async def test_subscription_absent():
    repo = AsyncMock()
    repo.find_subscription.return_value = None
    repo.create_subscription.return_value = None
    subs_service = SubscribeService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.CREATED
    repo.create_subscription.assert_called_once()


@pytest.mark.asyncio
async def test_subscription_find_subscription_db_error():
    repo = AsyncMock()
    repo.find_subscription.side_effect = SQLAlchemyError()
    subs_service = SubscribeService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.FAILED


@pytest.mark.asyncio
async def test_subscription_create_subscription_db_error():
    repo = AsyncMock()
    repo.find_subscription.return_value = None
    repo.create_subscription.side_effect = SQLAlchemyError()
    subs_service = SubscribeService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.FAILED


# --- subscribe_cmd() tests


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
    subs_service.subscribe.assert_called_once()


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
