import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from jobscraper.api.api import create_app
from jobscraper.pipelines.dispatch_pipeline import DispatchResult
from jobscraper.pipelines.scrape_pipeline import ScrapeResult


@pytest.fixture
def app_setup():
    app = create_app(bot=object(), dp=object())  # this is a bit silly
    app.state.bot = AsyncMock()
    app.state.dp = AsyncMock()
    client = TestClient(app, raise_server_exceptions=False)
    client.get("/health")
    return client, app


# --- /webhook tests ---


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


# --- /scrape tests


def test_scrape_no_error(app_setup):
    client, _ = app_setup
    scrape_result = ScrapeResult()
    scrape_result.ok = True
    scrape_result.new_jobs_processed = 2
    with patch(
        "jobscraper.api.api.scrape_and_create_notifications", return_value=scrape_result
    ) as scrape_and_create:
        resp = client.post("/scrape")
        data = resp.json()
        assert resp.status_code == 200
        scrape_and_create.assert_awaited_once()
        assert data["ok"] == scrape_result.ok
        assert data["new_jobs_processed"] == scrape_result.new_jobs_processed


def test_scrape_error(app_setup):
    client, _ = app_setup

    with patch(
        "jobscraper.api.api.scrape_and_create_notifications", side_effect=Exception()
    ):
        resp = client.post("/scrape")

        assert resp.status_code == 500


# --- /dispatch tests


def test_dispatch_no_error(app_setup):
    client, _ = app_setup
    result = DispatchResult()
    result.ok = True
    result.notifications_failed = 2
    result.notifications_sent = 10

    with patch(
        "jobscraper.api.api.dispatch_notifications", return_value=result
    ) as notifications:
        resp = client.post("/dispatch")
        data = resp.json()
        assert resp.status_code == 200
        notifications.assert_awaited_once()
        assert data["ok"] == result.ok
        assert data["notifications_failed"] == 2
        assert data["notifications_sent"] == 10


def test_dispatch_error(app_setup):
    client, _ = app_setup

    with patch("jobscraper.api.api.dispatch_notifications", side_effect=Exception()):
        resp = client.post("/dispatch")

        assert resp.status_code == 500
