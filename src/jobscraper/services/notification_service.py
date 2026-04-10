from typing import Sequence
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from jobscraper.models.job import JobStatus
from jobscraper.storage.models import (
    JobORM,
    NotificationORM,
    UserORM,
    UserSubscriptionORM,
)


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_for_job(self, job: JobORM) -> int:
        """Create notifications for all users matching a job. Returns count"""
        query = (
            select(UserORM)
            .join(UserSubscriptionORM, UserSubscriptionORM.user_id == UserORM.id)
            .where(
                and_(
                    UserSubscriptionORM.is_active,
                    UserSubscriptionORM.category == job.category,
                    UserSubscriptionORM.location == job.location,
                    UserSubscriptionORM.last_notified_at < job.created_at,
                )
            )
        )
        users_to_notify = (await self.session.execute(query)).scalars().all()
        for user in users_to_notify:
            notification = NotificationORM(user_id=user.id, job_id=job.id)
            self.session.add(notification)
        await self.session.commit()
        return len(users_to_notify)

    async def create_for_new_jobs(self, jobs: Sequence[JobORM]) -> int:
        """Create notifications for all NEW jobs. Returns total notifications created."""
        for job in jobs:
            await self.create_for_job(job)
            job.status = JobStatus.PROCESSED
        await self.session.commit()
        return len(jobs)
