from pydantic import BaseModel, Field
from datetime import UTC, datetime


class Payload(BaseModel):
    chat_id: int
    message: str


class UserUpdate(BaseModel):
    user_id: int
    chat_id: int
    username: str
    activity_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubscriptionUpdate(BaseModel):
    user_id: int
    action: str  # add, remove subscription
    category: str
    location: str
