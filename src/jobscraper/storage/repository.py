from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from jobscraper.storage.models import JobORM
from jobscraper.storage.mappers import to_orm

class JobRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, job):
        existing = await self.session.get(JobORM, job.id)
        if existing:
            for k, v in job.model_dump().items():
                setattr(existing, k, v)
        else:
            self.session.add(to_orm(job))
        await self.session.commit()

    async def get(self, job_id: str) -> Optional[JobORM]:
        return await self.session.get(JobORM, job_id)

    async def update_status(self, job_id: str, status: str):
        await self.session.execute(
            update(JobORM)
            .where(JobORM.id == job_id)
            .values(status=status)
        )
        await self.session.commit()
