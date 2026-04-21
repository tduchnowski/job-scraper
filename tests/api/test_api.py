import asyncio
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
    app.state.webhook_token = "123"
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
        headers={"X-Telegram-Bot-Api-Secret-Token": "123"},
    )

    assert response.status_code == 200
    app.state.dp.feed_update.assert_awaited_once()


def test_webhook_dispatch_error(app_setup):
    client, app = app_setup
    app.state.webhook_token = "123"
    app.state.dp.feed_update.side_effect = Exception()

    response = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "123"},
    )

    assert response.status_code == 200
    app.state.dp.feed_update.assert_awaited_once()


def test_webhook_invalid_json(app_setup):
    client, app = app_setup
    app.state.webhook_token = "123"

    response = client.post(
        "/webhook", data="not json", headers={"X-Telegram-Bot-Api-Secret-Token": "123"}
    )

    assert response.status_code == 200


def test_webhook_unauthorized(app_setup):
    client, app = app_setup
    app.state.webhook_token = "123"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "abc"}
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
        headers=headers,
    )

    assert response.status_code == 401
    app.state.dp.feed_update.assert_not_awaited()


# --- /scrape tests


def test_scrape_no_error(app_setup):
    client, app = app_setup
    app.state.api_key = "123"
    scrape_result = ScrapeResult()
    scrape_result.ok = True
    scrape_result.new_jobs_processed = 2
    with patch(
        "jobscraper.api.api.scrape_and_create_notifications", return_value=scrape_result
    ) as scrape_and_create:
        resp = client.post("/scrape", headers={"X-API-Key": "123"})
        data = resp.json()
        assert resp.status_code == 200
        scrape_and_create.assert_awaited_once()
        assert data["ok"] == scrape_result.ok
        assert data["new_jobs_processed"] == scrape_result.new_jobs_processed


def test_scrape_error(app_setup):
    client, app = app_setup
    app.state.api_key = "123"

    with patch(
        "jobscraper.api.api.scrape_and_create_notifications", side_effect=Exception()
    ):
        resp = client.post("/scrape", headers={"X-API-Key": "123"})

        assert resp.status_code == 500


def test_scrape_unauthorized(app_setup):
    client, app = app_setup
    app.state.api_key = "123"

    with patch(
        "jobscraper.api.api.scrape_and_create_notifications", side_effect=Exception()
    ) as create_notifications_mock:
        resp = client.post("/scrape", headers={"X-API-Key": "abc"})

        assert resp.status_code == 401
        create_notifications_mock.assert_not_awaited()


# --- /dispatch tests


def test_dispatch_no_error(app_setup):
    client, app = app_setup
    app.state.api_key = "123"
    result = DispatchResult()
    result.ok = True
    result.notifications_failed = 2
    result.notifications_sent = 10

    with patch(
        "jobscraper.api.api.dispatch_notifications", return_value=result
    ) as notifications:
        resp = client.post("/dispatch", headers={"X-API-Key": "123"})
        data = resp.json()
        assert resp.status_code == 200
        notifications.assert_awaited_once()
        assert data["ok"] == result.ok
        assert data["notifications_failed"] == 2
        assert data["notifications_sent"] == 10


def test_dispatch_error(app_setup):
    client, app = app_setup
    app.state.api_key = "123"

    with patch("jobscraper.api.api.dispatch_notifications", side_effect=Exception()):
        resp = client.post("/dispatch", headers={"X-API-Key": "123"})

        assert resp.status_code == 500


def test_dispatch_unauthorized(app_setup):
    client, app = app_setup
    app.state.api_key = "123"

    with patch(
        "jobscraper.api.api.dispatch_notifications", side_effect=Exception()
    ) as dispatch_notifications_mock:
        resp = client.post("/dispatch", headers={"X-API-Key": "abc"})

        assert resp.status_code == 401
        dispatch_notifications_mock.assert_not_awaited()


# --- /health tests


def test_health_returns_healthy_status(app_setup):
    client, _ = app_setup
    with patch("jobscraper.api.api.check_db_health", new_callable=AsyncMock):
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["checks"]["database"] == "healthy"


def test_health_returns_unhealthy_when_db_check_fails(app_setup):
    client, _ = app_setup
    with patch(
        "jobscraper.api.api.check_db_health",
        new_callable=AsyncMock,
        side_effect=Exception("db error"),
    ):
        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "unhealthy"
        assert data["error"] == "db error"


def test_health_returns_unhealthy_when_db_check_times_out(app_setup):
    client, _ = app_setup
    with patch(
        "jobscraper.api.api.check_db_health",
        new_callable=AsyncMock,
        side_effect=asyncio.TimeoutError,
    ):
        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "timeout"
        assert data["error"] == "Database timeout"
