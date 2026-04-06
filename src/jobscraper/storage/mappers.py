from jobscraper.storage.models import JobORM
from jobscraper.models.job import Job


def to_orm(job: Job) -> JobORM:
    return JobORM(**job.model_dump())


def to_pydantic(orm: JobORM) -> Job:
    return Job.model_validate(orm.__dict__)
