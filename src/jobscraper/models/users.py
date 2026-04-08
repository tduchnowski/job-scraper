from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class User(BaseModel):
    id: int = Field(...)
    chat_id: int = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # for debugging
    username: Optional[str] = None

    # for analytics
    last_interaction: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UserSubscription(BaseModel):
    id: str = Field(...)
    user_id: str
    is_active: bool = True

    category: Optional[str] = None
    location: Optional[str] = None

    last_notified_at: datetime = Field(
        default_factory=lambda: datetime.fromtimestamp(0, tz=timezone.utc)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
