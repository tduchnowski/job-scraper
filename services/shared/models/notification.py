from pydantic import BaseModel, Field

from services.shared.models.job import Job
from services.shared.models.user import User, UserSubscription


class Notification(BaseModel):
    id: str = Field(...)
    user: User
    job: Job
    subscription: UserSubscription
