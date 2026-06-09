from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    NEW = "NEW"
    PROCESSED = "PROCESSED"


class JobCategory(str, Enum):
    PYTHON = "PYTHON"
    JAVA = "JAVA"
    JAVASCRIPT = "JAVASCRIPT"
    TYPESCRIPT = "TYPESCRIPT"
    C = "C"
    GO = "GO"
    RUST = "RUST"
    PHP = "PHP"
    RUBY = "RUBY"
    SWIFT = "SWIFT"
    KOTLIN = "KOTLIN"
    WEB = "WEB"
    MOBILE = "MOBILE"
    DATA = "DATA"
    AI = "AI"
    CLOUD = "CLOUD"
    DEVOPS = "DEVOPS"
    SECURITY = "SECURITY"
    GAME = "GAME"
    BLOCKCHAIN = "BLOCKCHAIN"
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    FULLSTACK = "FULLSTACK"
    SRE = "SRE"
    QA = "QA"
    DATA_SCIENCE = "DATA_SCIENCE"


class JobLocation(str, Enum):
    POLAND = "POLAND"
    GERMANY = "GERMANY"
    IRELAND = "IRELAND"
    FRANCE = "FRANCE"
    SPAIN = "SPAIN"
    ITALY = "ITALY"
    NETHERLANDS = "NETHERLANDS"
    BELGIUM = "BELGIUM"
    SWEDEN = "SWEDEN"
    NORWAY = "NORWAY"
    DENMARK = "DENMARK"
    FINLAND = "FINLAND"
    SWITZERLAND = "SWITZERLAND"
    AUSTRIA = "AUSTRIA"
    SLOVAKIA = "SLOVAKIA"
    HUNGARY = "HUNGARY"
    ROMANIA = "ROMANIA"
    BULGARIA = "BULGARIA"
    PORTUGAL = "PORTUGAL"
    GREECE = "GREECE"
    UKRAINE = "UKRAINE"
    LITHUANIA = "LITHUANIA"
    LATVIA = "LATVIA"
    ESTONIA = "ESTONIA"

    CANADA = "CANADA"
    MEXICO = "MEXICO"

    BRAZIL = "BRAZIL"
    ARGENTINA = "ARGENTINA"
    CHILE = "CHILE"
    COLOMBIA = "COLOMBIA"

    ISRAEL = "ISRAEL"
    TURKEY = "TURKEY"
    UNITED_ARAB_EMIRATES = "UNITED_ARAB_EMIRATES"
    SAUDI_ARABIA = "SAUDI_ARABIA"
    QATAR = "QATAR"

    INDIA = "INDIA"
    PAKISTAN = "PAKISTAN"
    BANGLADESH = "BANGLADESH"

    SINGAPORE = "SINGAPORE"
    INDONESIA = "INDONESIA"
    MALAYSIA = "MALAYSIA"
    THAILAND = "THAILAND"
    VIETNAM = "VIETNAM"
    PHILIPPINES = "PHILIPPINES"

    CHINA = "CHINA"
    JAPAN = "JAPAN"
    SOUTH_KOREA = "SOUTH_KOREA"

    AUSTRALIA = "AUSTRALIA"
    NEW_ZEALAND = "NEW_ZEALAND"

    SOUTH_AFRICA = "SOUTH_AFRICA"
    EGYPT = "EGYPT"
    NIGERIA = "NIGERIA"
    KENYA = "KENYA"

    REMOTE = "REMOTE"


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(...)
    url: str
    title: str
    company: str

    category: Optional[JobCategory] = None
    location: Optional[JobLocation] = None
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
