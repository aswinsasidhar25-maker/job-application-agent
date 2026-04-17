from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
from config import settings


CSV_COLUMNS = [
    "title", "company", "location", "salary_min", "salary_max",
    "source", "job_url", "date_posted", "date_discovered",
    "match_score", "status", "description_summary",
]


def _ensure_dir():
    os.makedirs(os.path.dirname(settings.CSV_EXPORT_PATH), exist_ok=True)


def load_running_sheet() -> pd.DataFrame | None:
    if not os.path.exists(settings.CSV_EXPORT_PATH):
        return None
    try:
        df = pd.read_csv(settings.CSV_EXPORT_PATH)
        return df
    except Exception:
        return None


def export_jobs_to_csv(jobs) -> None:
    """Append new jobs to the running sheet CSV. Deduplicates by title+company+source."""
    if not jobs:
        return

    _ensure_dir()

    new_rows = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    for job in jobs:
        new_rows.append({
            "title": job.title or "",
            "company": job.company or "",
            "location": job.location or "",
            "salary_min": job.salary_min if job.salary_min else "",
            "salary_max": job.salary_max if job.salary_max else "",
            "source": job.source or "",
            "job_url": job.url or "",
            "date_posted": job.posted_date or "",
            "date_discovered": now,
            "match_score": str(int(job.cv_score)) if job.cv_score is not None else "",
            "status": job.status or "new",
            "description_summary": job.description_summary or "",
        })

    new_df = pd.DataFrame(new_rows, columns=CSV_COLUMNS)

    existing = load_running_sheet()
    if existing is not None and not existing.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["title", "company", "source"], keep="first"
        )
    else:
        combined = new_df

    combined.to_csv(settings.CSV_EXPORT_PATH, index=False)


def update_job_in_csv(job) -> None:
    """Update a single job's score and status in the running sheet."""
    existing = load_running_sheet()
    if existing is None or existing.empty:
        return

    mask = (
        (existing["title"] == (job.title or ""))
        & (existing["company"] == (job.company or ""))
        & (existing["source"] == (job.source or ""))
    )

    if mask.any():
        if job.cv_score is not None:
            existing.loc[mask, "match_score"] = str(int(job.cv_score))
        if job.status:
            existing.loc[mask, "status"] = job.status
        existing.to_csv(settings.CSV_EXPORT_PATH, index=False)
