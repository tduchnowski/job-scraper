from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    NEW = "NEW"
    PROCESSED = "PROCESSED"


class JobCategory(str, Enum):
    PYTHON = "PYTHON"
    AI = "AI"
    DATA_SCIENCE = "DATA SCIENCE"
    DEVOPS = "DEVOPS"


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(...)
    url: str
    title: str
    company: str

    category: Optional[JobCategory] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None  # full-time, contract, etc.
    skills: Optional[List[str]] = None
    seniority: Optional[str] = None
    summary: Optional[str] = None

    status: JobStatus = JobStatus.NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_at: Optional[datetime] = None
