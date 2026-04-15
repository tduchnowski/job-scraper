from datetime import datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Sequence, Tuple

from sqlalchemy.orm.strategy_options import selectinload

from jobscraper.models.job import Job, JobStatus
from jobscraper.storage.models import JobORM, NotificationORM, UserSubscriptionORM
from jobscraper.storage.mappers import job_to_orm


class UpsertResult(Enum):
    CREATED = "created"
    UPDATED = "updated"


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, job: Job) -> Tuple[JobORM, UpsertResult]:
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
        """
        Upsert batch of jobs and return if the operation was successful
        """
        jobs_orm = [job_to_orm(job) for job in jobs]
        for job_orm in jobs_orm:
            await self.session.merge(job_orm)
        return len(jobs_orm)

    async def get(self, job_id: str) -> Optional[JobORM]:
        return await self.session.get(JobORM, job_id)

    async def get_new_jobs(self) -> Sequence[JobORM]:
        query = (
            select(JobORM)
            .where(JobORM.status == JobStatus.NEW)
            .order_by(JobORM.created_at.asc())
        )
        res = await self.session.execute(query)
        return res.scalars().all()

    async def update_status(self, job_id: str, status: str):
        await self.session.execute(
            update(JobORM).where(JobORM.id == job_id).values(status=status)
        )
        await self.session.commit()


class UserSubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_subscriptions(
        self, user_id: int
    ) -> Sequence[UserSubscriptionORM]:
        stmt = select(UserSubscriptionORM).where(
            and_(UserSubscriptionORM.user_id == user_id),
            UserSubscriptionORM.is_active,
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def find_subscription(
        self, user_id: int, category: str, location: str
    ) -> UserSubscriptionORM | None:
        stmt = select(UserSubscriptionORM).where(
            and_(UserSubscriptionORM.user_id == user_id),
            UserSubscriptionORM.is_active,
            UserSubscriptionORM.category == category,
            UserSubscriptionORM.location == location,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_pending(self) -> Sequence[NotificationORM]:
        stmt = (
            select(NotificationORM)
            .where(
                and_(
                    NotificationORM.status == "pending",
                    NotificationORM.next_attempt_at <= datetime.now(timezone.utc),
                )
            )
            .order_by(
                NotificationORM.created_at.asc()  # Oldest first
            )
            .limit(100)
            .options(
                selectinload(NotificationORM.user), selectinload(NotificationORM.job)
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_successful(self, notification: NotificationORM):
        notification.status = "sent"
        notification.last_attempt_at = datetime.now(timezone.utc)

    def mark_failed(
        self, notification: NotificationORM, retry_delay: float | None = None
    ):
        notification.attempts += 1
        notification.last_attempt_at = datetime.now(timezone.utc)

        if notification.attempts >= 3:
            self.mark_permanently_failed(notification)
        else:
            delay = retry_delay
            if retry_delay is None:
                delay = 60 * (2**notification.attempts)  # 2, 4, 8 minutes
            else:
                delay = retry_delay

            # Retry in exponential backoff: 5min, 30min, 2h
            notification.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay
            )

    def mark_permanently_failed(self, notification: NotificationORM):
        notification.status = "failed"


# class UserRepository:
#     def __init__(self, session: AsyncSession):
#         self.session = session
#
#     def
#
