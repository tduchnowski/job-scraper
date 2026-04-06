from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional, List

from jobscraper.storage.base import Base

class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String)

    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String, default="NEW")
    retries: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
