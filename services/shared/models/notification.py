from pydantic import BaseModel

from services.shared.models.job import Job
from services.shared.models.user import User, UserSubscription


class Notification(BaseModel):
    id: str
    user: User
    job: Job
    subscription: UserSubscription
