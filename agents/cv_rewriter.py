import json
import os
from sqlalchemy.orm import Session
from services.llm_client import llm_call
from models.job import Job
from models.user import UserProfile
from config import settings


def _load_prompt():
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "rewrite_cv.txt")
    with open(path) as f:
        return f.read().strip()


def rewrite_cv_for_job(db: Session, profile: UserProfile, job: Job) -> str:
    """Rewrite CV tailored for a specific job. Uses FULL model (expensive, on-demand only)."""
    system = _load_prompt()
    prompt = (
        f"TARGET JOB:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Key Requirements: {job.requirements if isinstance(job.requirements, str) else json.dumps(job.requirements or [])}\n\n"
        f"CURRENT CV:\n{profile.parsed_cv_text[:4000]}"
    )

    response = llm_call(
        db=db,
        prompt=prompt,
        task_type="rewrite",
        system=system,
        model=settings.FULL_MODEL,
        use_cache=True,
        cache_ttl=720,  # 30 days
        json_mode=False,  # We want markdown, not JSON
    )

    # Save rewritten CV to file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"rewritten_cv_{job.id}.md"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    with open(filepath, "w") as f:
        f.write(response)

    job.rewritten_cv_path = filepath
    db.commit()

    return response
