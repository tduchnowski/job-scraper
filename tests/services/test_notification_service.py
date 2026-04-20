import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from jobscraper.services.notification_service import NotificationService
from jobscraper.storage.models import JobORM
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_create_for_job_with_no_matching_subscriptions_returns_zero(
        self, mock_session
    ):
        """When no users match the job's category/location, return 0."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        service = NotificationService(mock_session)
        job = JobORM(
            id="123",
            category="GO",
            location="Warsaw",
            created_at=datetime.now(timezone.utc),
        )

        result = await service.create_for_job(job)

        assert result == 0

    @pytest.mark.asyncio
    async def test_create_for_job_returns_count_when_users_match(self, mock_session):
        """When users match job, return the count of notifications created."""
        mock_result = MagicMock()
        mock_result.all.return_value = [(1, 10), (2, 20)]
        mock_session.execute.return_value = mock_result

        service = NotificationService(mock_session)
        job = JobORM(
            id="123",
            category="GO",
            location="Warsaw",
            created_at=datetime.now(timezone.utc),
        )

        result = await service.create_for_job(job)

        assert result == 2

    @pytest.mark.asyncio
    async def test_create_for_new_jobs_processes_all_jobs(self, mock_session):
        """create_for_new_jobs processes each job in the list."""
        mock_result = MagicMock()
        mock_result.all.return_value = [(1, 10)]
        mock_session.execute.return_value = mock_result

        service = NotificationService(mock_session)
        jobs = [
            JobORM(
                id="1",
                category="GO",
                location="Warsaw",
                created_at=datetime.now(timezone.utc),
            ),
            JobORM(
                id="2",
                category="GO",
                location="Berlin",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        await service.create_for_new_jobs(jobs)

        # Each job: 1 select + 1 insert = 2 calls per job
        assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_create_for_job_raises_on_db_error(self, mock_session):
        """Database errors propagate to caller."""
        mock_session.execute.side_effect = SQLAlchemyError("DB error")

        service = NotificationService(mock_session)
        job = JobORM(
            id="123",
            category="GO",
            location="Warsaw",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(SQLAlchemyError):
            await service.create_for_job(job)
