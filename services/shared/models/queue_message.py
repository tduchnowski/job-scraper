from enum import Enum

from pydantic import BaseModel, Field
from datetime import UTC, datetime


class Payload(BaseModel):
    chat_id: int
    message: str


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
