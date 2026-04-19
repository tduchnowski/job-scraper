import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from jobscraper.storage.repository import (
    JobRepository,
    UserRepository,
    UserSubscriptionRepository,
    NotificationRepository,
    UpsertResult,
)
from jobscraper.models.job import Job, JobStatus
from jobscraper.storage.models import JobORM, NotificationORM


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestJobRepository:
    @pytest.mark.asyncio
    async def test_upsert_creates_new_job(self, mock_session):
        job = Job(id="123", title="Dev", company="Acme", url="http://example.com")
        mock_session.get.return_value = None

        repo = JobRepository(mock_session)
        orm_obj, result = await repo.upsert(job)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result == UpsertResult.CREATED

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_job(self, mock_session):
        job = Job(id="123", title="Dev", company="Acme", url="http://example.com")
        existing_job = MagicMock()
        mock_session.get.return_value = existing_job

        repo = JobRepository(mock_session)
        orm_obj, result = await repo.upsert(job)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()
        assert result == UpsertResult.UPDATED

    @pytest.mark.asyncio
    async def test_get_returns_job_by_id(self, mock_session):
        mock_session.get.return_value = MagicMock()

        repo = JobRepository(mock_session)
        result = await repo.get("123")

        mock_session.get.assert_called_once_with(JobORM, "123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_new_jobs_returns_new_status(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = JobRepository(mock_session)
        result = await repo.get_new_jobs()

        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_status(self, mock_session):
        mock_session.execute.return_value = MagicMock()

        repo = JobRepository(mock_session)
        await repo.update_status("123", JobStatus.PROCESSED)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestUserRepository:
    @pytest.mark.asyncio
    async def test_add_or_update_creates_new_user(self, mock_session):
        mock_session.get.return_value = None

        repo = UserRepository(mock_session)
        await repo.add_or_update(1, 123, "testuser")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_or_update_updates_existing_user(self, mock_session):
        existing_user = MagicMock()
        mock_session.get.return_value = existing_user

        repo = UserRepository(mock_session)
        await repo.add_or_update(1, 123, "testuser")

        mock_session.add.assert_not_called()


class TestUserSubscriptionRepository:
    @pytest.mark.asyncio
    async def test_get_user_subscriptions(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = UserSubscriptionRepository(mock_session)
        result = await repo.get_user_subscriptions(1)

        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_create_subscription(self, mock_session):
        repo = UserSubscriptionRepository(mock_session)
        await repo.create_subscription(1, "GO", "Warsaw")

        mock_session.add.assert_called_once()
        call_args = mock_session.add.call_args[0][0]
        assert call_args.user_id == 1
        assert call_args.category == "GO"
        assert call_args.location == "Warsaw"
        assert call_args.is_active is True

    @pytest.mark.asyncio
    async def test_find_subscription(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(
                        scalar_one_or_none=AsyncMock(return_value=None)
                    )
                )
            )
        )

        repo = UserSubscriptionRepository(mock_session)
        await repo.find_subscription(1, "GO", "Warsaw")

        mock_session.execute.assert_called_once()


class TestNotificationRepository:
    @pytest.mark.asyncio
    async def test_get_all_pending(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = NotificationRepository(mock_session)
        result = await repo.get_all_pending(limit=100)

        mock_session.execute.assert_called_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_mark_successful(self, mock_session):
        notification = NotificationORM(status="pending")
        notification.last_attempt_at = None

        repo = NotificationRepository(mock_session)
        await repo.mark_successful(notification)

        assert notification.status == "sent"
        assert notification.last_attempt_at is not None

    def test_mark_failed_first_attempt(self):
        notification = NotificationORM(status="pending")
        notification.attempts = 0
        notification.last_attempt_at = None
        next_attempt = datetime.now(timezone.utc)
        notification.next_attempt_at = next_attempt

        repo = NotificationRepository(AsyncMock())
        repo.mark_failed(notification)

        assert notification.attempts == 1
        assert notification.next_attempt_at > next_attempt

    def test_mark_failed_permanently_after_three(self):
        notification = NotificationORM(status="pending")
        notification.attempts = 2
        notification.last_attempt_at = None
        next_attempt = datetime.now(timezone.utc)
        notification.next_attempt_at = next_attempt

        repo = NotificationRepository(AsyncMock())
        repo.mark_failed(notification)

        assert notification.status == "failed"

    def test_mark_permanently_failed(self):
        notification = NotificationORM(status="pending")

        repo = NotificationRepository(AsyncMock())
        repo.mark_permanently_failed(notification)

        assert notification.status == "failed"
