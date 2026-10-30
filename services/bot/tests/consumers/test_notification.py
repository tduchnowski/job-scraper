import pytest
from unittest.mock import AsyncMock

from redisaq import Message
from services.bot.src.consumers.notification import UserMessageProcessor
from services.shared.models.queue_message import NotificationStatus


@pytest.fixture
def user_msg_processor() -> UserMessageProcessor:
    """
    Provides a UserMessageProcessor with fully mocked async dependencies.
    """
    mock_bot = AsyncMock()
    mock_producer = AsyncMock()

    processor = UserMessageProcessor(
        bot=mock_bot, notification_status_producer=mock_producer
    )

    return processor


@pytest.mark.asyncio
async def test_emit_notification_update_skips_empty_ids(user_msg_processor):
    """make sure empty messages are not pushed to Redis"""
    await user_msg_processor._emit_notification_update([], NotificationStatus.SUCCESS)
    await user_msg_processor._emit_notification_update(None, NotificationStatus.SUCCESS)

    user_msg_processor.notification_status_producer.batch_enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_emit_notification_update_correct_batch(user_msg_processor):
    """test if correct batch is enqueued"""
    await user_msg_processor._emit_notification_update(
        [10, 11, 12], NotificationStatus.SUCCESS
    )

    expected_batch = [
        {"notification_id": 10, "status": 0},
        {"notification_id": 11, "status": 0},
        {"notification_id": 12, "status": 0},
    ]
    user_msg_processor.notification_status_producer.batch_enqueue.assert_called_with(
        expected_batch
    )


@pytest.mark.asyncio
async def test_process_valid_message(user_msg_processor):
    chat_id = 1
    text = "job1, job2"
    payload = {"chat_id": chat_id, "message": text, "notification_ids": [1, 2]}
    msg = Message(topic="smth", payload=payload)
    await user_msg_processor.process(msg)
    expected_batch = [
        {"notification_id": 1, "status": 0},
        {"notification_id": 2, "status": 0},
    ]
    user_msg_processor.bot.send_message.assert_called_with(chat_id=chat_id, text=text)
    user_msg_processor.notification_status_producer.batch_enqueue.assert_called_with(
        expected_batch
    )


@pytest.mark.asyncio
async def test_process_invalid_message(user_msg_processor):
    """test that in case of invalid message neither bot nor redis producer is being used"""
    payload = {}
    msg = Message(topic="smth", payload=payload)
    await user_msg_processor.process(msg)
    user_msg_processor.bot.send_message.assert_not_called()
    user_msg_processor.notification_status_producer.batch_enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_process_bot_general_exception(user_msg_processor):
    chat_id = 1
    text = "job1, job2"
    payload = {"chat_id": chat_id, "message": text, "notification_ids": [1, 2]}
    msg = Message(topic="smth", payload=payload)
    user_msg_processor.bot.send_message.side_effect = Exception()
    await user_msg_processor.process(msg)
    expected_batch = [
        {"notification_id": 1, "status": 1},
        {"notification_id": 2, "status": 1},
    ]
    user_msg_processor.notification_status_producer.batch_enqueue.assert_called_with(
        expected_batch
    )


@pytest.mark.asyncio
async def test_process_user_blocked_exception(user_msg_processor):
    """test if notifications are marked as permanently failed for blocked users"""
    # TODO
    pass
