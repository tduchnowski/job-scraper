from typing import Sequence
from sqlalchemy import and_, insert, select
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

    async def create_for_job(self, job: JobORM):
        """Create notifications for all users matching a job. Returns count"""
        query = (
            select(UserORM.id)
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
        user_ids = (await self.session.execute(query)).scalars().all()
        print(user_ids)
        if not user_ids:
            return 0

        # INSERT OR IGNORE
        stmt = (
            insert(NotificationORM)
            .values([{"user_id": uid, "job_id": job.id} for uid in user_ids])
            .prefix_with("OR IGNORE")
        )
        await self.session.execute(stmt)

    async def create_for_new_jobs(self, jobs: Sequence[JobORM]):
        """Create notifications for all NEW jobs. Returns total notifications created."""
        for job in jobs:
            await self.create_for_job(job)
            job.status = JobStatus.PROCESSED
            await self.session.commit()
