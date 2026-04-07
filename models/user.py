from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime
from database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), default="")
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    location = Column(String(200), default="")
    preferred_roles = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(String(50), default="any")  # remote/hybrid/onsite/any
    min_salary = Column(Float, nullable=True)
    experience_summary = Column(Text, default="")
    projects_summary = Column(Text, default="")
    skills = Column(JSON, default=list)
    raw_cv_path = Column(String(500), default="")
    parsed_cv_text = Column(Text, default="")
    structured_cv = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
