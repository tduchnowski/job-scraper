from datetime import datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Sequence, Tuple

from sqlalchemy.orm.strategy_options import selectinload

from jobscraper.models.job import Job, JobStatus
from jobscraper.storage.models import (
    JobORM,
    NotificationORM,
    UserORM,
    UserSubscriptionORM,
)
from jobscraper.storage.mappers import job_to_orm


class UpsertResult(Enum):
    CREATED = "created"
    UPDATED = "updated"


class JobRepository:
    """Repository for Job CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, job: Job) -> Tuple[JobORM, UpsertResult]:
        """Insert job if not exists, otherwise update. Returns ORM object and result."""
        existing = await self.session.get(JobORM, job.id)

        if existing:
            for k, v in job.model_dump().items():
                setattr(existing, k, v)
            result = UpsertResult.UPDATED
            orm_obj = existing
        else:
            orm_obj = job_to_orm(job)
            self.session.add(orm_obj)
            result = UpsertResult.CREATED

        await self.session.commit()
        return orm_obj, result

    async def upsert_batch(self, jobs: list[Job]) -> int:
        """Upsert batch of jobs. Returns count of jobs processed."""
        jobs_orm = [job_to_orm(job) for job in jobs]
        for job_orm in jobs_orm:
            await self.session.merge(job_orm)
        return len(jobs_orm)

    async def get(self, job_id: str) -> Optional[JobORM]:
        """Get job by ID."""
        return await self.session.get(JobORM, job_id)

    async def get_new_jobs(self) -> Sequence[JobORM]:
        """Get all jobs with NEW status, ordered by creation date."""
        query = (
            select(JobORM)
            .where(JobORM.status == JobStatus.NEW)
            .order_by(JobORM.created_at.asc())
        )
        res = await self.session.execute(query)
        return res.scalars().all()

    async def update_status(self, job_id: str, status: str):
        """Update job status."""
        await self.session.execute(
            update(JobORM).where(JobORM.id == job_id).values(status=status)
        )
        await self.session.commit()


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_or_update(self, user_id: int, chat_id: int, username: str | None):
        """Create new user or update last_interaction for existing."""
        user = await self.session.get(UserORM, user_id)
        if not user:
            user = UserORM(
                id=user_id,
                chat_id=chat_id,
                username=username,
                created_at=datetime.now(timezone.utc),
                last_interaction=datetime.now(timezone.utc),
            )
            self.session.add(user)
        else:
            user.last_interaction = datetime.now(timezone.utc)


class UserSubscriptionRepository:
    """Repository for UserSubscription CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_subscriptions(
        self, user_id: int
    ) -> Sequence[UserSubscriptionORM]:
        """Get all active subscriptions for a user."""
        stmt = select(UserSubscriptionORM).where(
            and_(UserSubscriptionORM.user_id == user_id),
            UserSubscriptionORM.is_active,
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def create_subscription(self, user_id: int, category: str, location: str):
        """Create a new subscription for user."""
        subscription = UserSubscriptionORM(
            user_id=user_id,
            category=category,
            location=location,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_notified_at=datetime.fromtimestamp(0, tz=timezone.utc),
        )
        self.session.add(subscription)

    async def find_subscription(
        self, user_id: int, category: str, location: str
    ) -> UserSubscriptionORM | None:
        """Find active subscription by user/category/location."""
        stmt = select(UserSubscriptionORM).where(
            and_(
                UserSubscriptionORM.user_id == user_id,
                UserSubscriptionORM.is_active,
                UserSubscriptionORM.category == category,
                UserSubscriptionORM.location == location,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class NotificationRepository:
    """Repository for Notification CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_pending(self, limit=2000) -> Sequence[NotificationORM]:
        """Get pending notifications due for delivery, randomly ordered."""
        stmt = (
            select(NotificationORM)
            .where(
                and_(
                    NotificationORM.status == "pending",
                    NotificationORM.next_attempt_at <= datetime.now(timezone.utc),
                )
            )
            .order_by(func.random())
            .limit(limit)
            .options(
                selectinload(NotificationORM.user), selectinload(NotificationORM.job)
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_successful(self, notification: NotificationORM):
        """Mark notification as sent."""
        notification.status = "sent"
        notification.last_attempt_at = datetime.now(timezone.utc)

    def mark_failed(
        self, notification: NotificationORM, retry_delay: float | None = None
    ):
        """Mark notification as failed. Schedules retry with exponential backoff (2/4/8 min)."""
        notification.attempts += 1
        notification.last_attempt_at = datetime.now(timezone.utc)

        if notification.attempts >= 3:
            self.mark_permanently_failed(notification)
        else:
            delay = retry_delay
            if retry_delay is None:
                delay = 60 * (2**notification.attempts)
            else:
                delay = retry_delay

            notification.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay
            )

    def mark_permanently_failed(self, notification: NotificationORM):
        """Mark notification as permanently failed after max retries."""
        notification.status = "failed"
