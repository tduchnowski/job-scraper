import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.handlers.subscribe import SubscriptionResult, SubscribeService


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
async def test_invalid_args():
    pass
