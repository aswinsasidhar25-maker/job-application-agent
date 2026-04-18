from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime
from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(200), default="")
    source = Column(String(50), default="")  # serpapi/adzuna/remotive/scraper
    title = Column(String(500), default="")
    company = Column(String(300), default="")
    location = Column(String(300), default="")
    remote_type = Column(String(50), default="")  # remote/hybrid/onsite/unknown
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    description_raw = Column(Text, default="")
    description_summary = Column(Text, default="")
    requirements = Column(Text, default="[]")
    url = Column(String(1000), default="")
    posted_date = Column(String(100), default="")
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default="new")  # new/saved/applied/interviewing/rejected/dismissed
    cv_score = Column(Float, nullable=True)
    score_explanation = Column(Text, default="")
    score_details = Column(Text, default="{}")  # {matches: [], gaps: []}
    rewritten_cv_path = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
