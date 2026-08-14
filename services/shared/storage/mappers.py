from jobscraper.storage.models import JobORM, UserORM, UserSubscriptionORM
from jobscraper.models.job import Job
from jobscraper.models.users import User, UserSubscription


def job_to_orm(job: Job) -> JobORM:
    return JobORM(**job.model_dump())


def job_to_pydantic(orm: JobORM) -> Job:
    return Job.model_validate(orm)


def user_to_orm(user: User) -> UserORM:
    return UserORM(**user.model_dump())


def user_to_pydantic(orm: UserORM) -> User:
    return User.model_validate(orm)


def sub_to_orm(sub: UserSubscription) -> UserSubscriptionORM:
    return UserSubscriptionORM(**sub.model_dump())


def sub_to_pydantic(orm: UserSubscriptionORM) -> UserSubscription:
    return UserSubscription.model_validate(orm)
