from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class Job(BaseModel):
    id: str = Field(..., description="Indeed job key (jk)")
    url: str

    title: str
    company: str
    location: Optional[str] = None

    description: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None  # full-time, contract, etc.

    skills: Optional[List[str]] = None
    seniority: Optional[str] = None
    summary: Optional[str] = None

    status: JobStatus = JobStatus.NEW
    retries: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_at: Optional[datetime] = None
