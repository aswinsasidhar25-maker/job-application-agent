"""Pure Python orchestrator. NO LLM calls here - just dispatch logic.
This is the biggest token saver vs an autonomous agent loop."""
from __future__ import annotations

from sqlalchemy.orm import Session
from models.user import UserProfile
from models.job import Job


def get_profile(db: Session) -> UserProfile | None:
    return db.query(UserProfile).first()


def has_profile(db: Session) -> bool:
    return db.query(UserProfile).first() is not None


def has_cv(db: Session) -> bool:
    profile = get_profile(db)
    return bool(profile and profile.parsed_cv_text)


def get_jobs(db: Session, status: str | None = None, min_score: float | None = None) -> list[Job]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if min_score is not None:
        # Only exclude jobs that have a score AND it's below the threshold
        # Unscored jobs (NULL) always pass through
        from sqlalchemy import or_
        query = query.filter(
            or_(Job.cv_score >= min_score, Job.cv_score == None)  # noqa: E711
        )
    return query.order_by(Job.cv_score.desc().nullsfirst()).all()


def get_job(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def update_job_status(db: Session, job_id: int, status: str) -> Job | None:
    job = get_job(db, job_id)
    if job:
        job.status = status
        db.commit()
        db.refresh(job)
        from services.csv_export import update_job_in_csv
        update_job_in_csv(job)
    return job


def get_dashboard_stats(db: Session) -> dict:
    from models.cache import TokenUsage
    from datetime import datetime, timezone

    total_jobs = db.query(Job).count()
    new_jobs = db.query(Job).filter(Job.status == "new").count()
    saved_jobs = db.query(Job).filter(Job.status == "saved").count()
    applied_jobs = db.query(Job).filter(Job.status == "applied").count()
    interviewing = db.query(Job).filter(Job.status == "interviewing").count()

    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_rows = db.query(TokenUsage).filter(TokenUsage.timestamp >= start_of_month).all()

    total_cost = sum(r.cost_usd for r in usage_rows)
    total_tokens = sum(r.tokens_input + r.tokens_output for r in usage_rows)
    cost_by_task = {}
    for r in usage_rows:
        cost_by_task[r.task_type] = cost_by_task.get(r.task_type, 0) + r.cost_usd

    return {
        "total_jobs": total_jobs,
        "new_jobs": new_jobs,
        "saved_jobs": saved_jobs,
        "applied_jobs": applied_jobs,
        "interviewing": interviewing,
        "monthly_cost": round(total_cost, 4),
        "monthly_tokens": total_tokens,
        "cost_by_task": cost_by_task,
    }
