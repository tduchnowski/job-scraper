from unittest.mock import AsyncMock, patch

import pytest
from services.bot.src.handlers.unsubscribe import unsubscribe_cmd


@pytest.mark.asyncio
async def test_unsubscribe_wrong_args():
    message, subs_service = AsyncMock(), AsyncMock()
    message.text = "/unsubscribe onlyonearg"
    message.from_user.id = 1

    with patch(
        "services.bot.src.handlers.unsubscribe.are_args_valid",
        return_value=(False, "error"),
    ):
        await unsubscribe_cmd(message, subs_service=subs_service)

    message.answer.assert_called_once_with("error", parse_mode="markdown")
    subs_service.unsubscribe.assert_not_called()
