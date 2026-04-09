from sqlalchemy import (
    Index,
    String,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List

from jobscraper.models.job import JobCategory, JobStatus
from jobscraper.storage.base import Base


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    category: Mapped[Optional[JobCategory]] = mapped_column(
        SAEnum(JobCategory), nullable=True
    )
    location: Mapped[str] = mapped_column(String, nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.NEW)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.fromtimestamp(0, tz=timezone.utc)
    )
    scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)  # Telegram user_id
    chat_id: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_interaction: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subscriptions: Mapped[list["UserSubscriptionORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSubscriptionORM(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    category: Mapped[JobCategory] = mapped_column(SAEnum(JobCategory), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_notified_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.fromtimestamp(0, tz=timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["UserORM"] = relationship(back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "category", "location", name="unique_user_subscription"
        ),
    )


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # --- delivery state ---
    status: Mapped[str] = mapped_column(
        default="pending",  # pending | processing | sent | failed
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    # --- retry control ---
    next_attempt_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # --- timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["UserORM"] = relationship(foreign_keys=[user_id])
    job: Mapped["JobORM"] = relationship(foreign_keys=[job_id])

    # --- constraints ---
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_notification"),
        Index("idx_notifications_status_next_attempt", "status", "next_attempt_at"),
        Index("idx_notifications_user_id", "user_id"),
    )
