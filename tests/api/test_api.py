import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from jobscraper.api.api import create_app


@pytest.fixture
def app_setup():
    app = create_app(bot=object(), dp=object())  # this is a bit silly
    app.state.bot = AsyncMock()
    app.state.dp = AsyncMock()
    client = TestClient(app)
    client.get("/health")
    return client, app


def test_webhook_success(app_setup):
    client, app = app_setup
    response = client.post(
        "/webhook",
        json={
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 1, "type": "private"},
            },
        },
    )

    assert response.status_code == 200
    app.state.dp.feed_update.assert_awaited_once()


def test_webhook_dispatch_error(app_setup):
    client, app = app_setup
    app.state.dp.feed_update.side_effect = Exception()

    response = client.post("/webhook", json={"update_id": 1})

    assert response.status_code == 200
    app.state.dp.feed_update.assert_awaited_once()


def test_webhook_invalid_json(app_setup):
    client, _ = app_setup

    response = client.post("/webhook", data="not json")

    assert response.status_code == 200
