import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{settings.DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models.user import UserProfile  # noqa: F401
    from models.job import Job  # noqa: F401
    from models.cache import LLMCache, TokenUsage  # noqa: F401

    Base.metadata.create_all(bind=engine)
