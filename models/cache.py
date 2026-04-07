from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from database import Base


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_hash = Column(String(64), unique=True, index=True)
    model = Column(String(100), default="")
    response_text = Column(Text, default="")
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ttl_hours = Column(Integer, default=720)  # 30 days default


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), default="")  # score/rewrite/search/onboard/summarize
    model = Column(String(100), default="")
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
