import pytest
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.exc import SQLAlchemyError

from jobscraper.bot.subscription_service import (
    RemoveSubscriptionResult,
    SubscriptionResult,
    SubscriptionService,
)


@pytest.mark.asyncio
async def test_subscription_exists():
    repo = AsyncMock()
    repo.find_subscription.return_value = object()
    subs_service = SubscriptionService(None)
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
    subs_service = SubscriptionService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.CREATED
    repo.create_subscription.assert_called_once()


@pytest.mark.asyncio
async def test_subscription_find_subscription_db_error():
    repo = AsyncMock()
    repo.find_subscription.side_effect = SQLAlchemyError()
    subs_service = SubscriptionService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.FAILED


@pytest.mark.asyncio
async def test_subscription_create_subscription_db_error():
    repo = AsyncMock()
    repo.find_subscription.return_value = None
    repo.create_subscription.side_effect = SQLAlchemyError()
    subs_service = SubscriptionService(None)
    res = await subs_service.create_subscription(
        repo, user_id=1, category="X", location="P"
    )
    assert res == SubscriptionResult.FAILED


@pytest.mark.asyncio
async def test_unsubscribe_not_exist():
    repo = AsyncMock()
    repo.find_subscription.return_value = None

    service = SubscriptionService(None)

    res = await service.delete_subscription(repo, user_id=1, category="X", location="P")

    assert res == RemoveSubscriptionResult.NOT_EXIST


@pytest.mark.asyncio
async def test_unsubscribe_existing_marks_inactive():
    sub = AsyncMock()
    sub.is_active = True

    repo = AsyncMock()
    repo.find_subscription.return_value = sub

    service = SubscriptionService(None)

    res = await service.delete_subscription(repo, user_id=1, category="X", location="P")

    assert res == RemoveSubscriptionResult.REMOVED
    assert sub.is_active is False


@pytest.mark.asyncio
async def test_unsubscribe_find_db_error():
    repo = AsyncMock()
    repo.find_subscription.side_effect = SQLAlchemyError()

    service = SubscriptionService(None)

    res = await service.delete_subscription(repo, user_id=1, category="X", location="P")

    assert res == RemoveSubscriptionResult.FAILED


@pytest.mark.asyncio
async def test_unsubscribe_commits():
    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    session_factory = Mock(return_value=session_cm)

    service = SubscriptionService(session_factory)

    repo = AsyncMock()
    repo.find_subscription.return_value = None

    with patch(
        "jobscraper.bot.subscription_service.UserSubscriptionRepository",
        return_value=repo,
    ):
        await service.unsubscribe(1, "X", "P")

    session.commit.assert_awaited_once()
