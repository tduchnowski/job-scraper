from enum import Enum
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Sequence, Tuple

from jobscraper.models.job import Job, JobStatus
from jobscraper.storage.models import JobORM
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

    async def get(self, job_id: str) -> Optional[JobORM]:
        return await self.session.get(JobORM, job_id)

    async def get_new_jobs(self, limit: int = 100) -> Sequence[JobORM]:
        query = (
            select(JobORM)
            .where(JobORM.status == JobStatus.NEW)
            .order_by(JobORM.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(query)
        return res.scalars().all()

    async def update_status(self, job_id: str, status: str):
        await self.session.execute(
            update(JobORM).where(JobORM.id == job_id).values(status=status)
        )
        await self.session.commit()
