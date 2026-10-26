from enum import Enum, IntEnum

from pydantic import BaseModel, Field
from datetime import UTC, datetime

from services.shared.models.job import JobCategory, JobStatus


class TelegramUserMessage(BaseModel):
    chat_id: int
    message: str
    notification_ids: list[int] | None = (
        None  # in case the message is a job notification
    )


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
    chat_id: int
    operation: SubscribeOperation  # add, remove subscription
    category: str
    location: str


class NotificationStatus(IntEnum):
    SUCCESS = 0
    FAIL = 1
    PERMANENT_FAIL = 2


class NotificationUpdate(BaseModel):
    notification_id: int
    status: NotificationStatus  # was notification delivered successfully or not


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
