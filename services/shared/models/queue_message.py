from enum import Enum

from pydantic import BaseModel, Field
from datetime import UTC, datetime

from services.shared.storage.models import NotificationStatus
from services.shared.models.job import JobCategory, JobStatus


class Payload(BaseModel):
    chat_id: int
    message: str


# class TelegramNotification(BaseModel):
#     chat_id: int
#     notification_id: int
#     job: Job


class UserActivity(BaseModel):
    user_id: int
    chat_id: int
    username: str
    activity_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubscribeOperation(Enum):
    ADD = 0
    REMOVE = 1


class SubscriptionUpdate(BaseModel):
    user_id: int
    operation: SubscribeOperation  # add, remove subscription
    category: str
    location: str


class NotificationUpdate(BaseModel):
    notification_id: int
    status: NotificationStatus


class NewNotification(BaseModel):
    user_id: int
    job_id: str
    subscription_id: int


class JobUpdate(BaseModel):
    job_id: str
    status: JobStatus


class NewJob(BaseModel):
    id: str
    url: str
    title: str
    company: str
    category: JobCategory
    location: str
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
