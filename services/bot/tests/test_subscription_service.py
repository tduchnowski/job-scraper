import pytest
from unittest.mock import AsyncMock

from services.bot.src.subscription_service import SubscriptionService
from services.shared.models.queue_message import SubscribeOperation


@pytest.mark.asyncio
async def test_update_no_errors():
    mock_producer = AsyncMock()
    subs_service = SubscriptionService(mock_producer)
    update_res = await subs_service.update(
        1, 1, "Python", "Poland", SubscribeOperation.ADD
    )
    assert update_res
    mock_producer.enqueue.assert_called_once()


@pytest.mark.asyncio
async def test_update_error():
    mock_producer = AsyncMock()
    mock_producer.enqueue.side_effect = Exception()
    subs_service = SubscriptionService(mock_producer)
    update_res = await subs_service.update(
        1, 1, "Python", "Poland", SubscribeOperation.ADD
    )
    assert not update_res
    mock_producer.enqueue.assert_called_once()
