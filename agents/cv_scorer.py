from __future__ import annotations

import json
import os
from sqlalchemy.orm import Session
from services.llm_client import llm_call
from models.job import Job
from models.user import UserProfile


def _load_prompt():
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "score_cv.txt")
    with open(path) as f:
        return f.read().strip()


def _keyword_overlap(skills: list[str], requirements: list[str]) -> float:
    """Rule-based pre-filter. Returns overlap ratio 0-1. Zero LLM tokens."""
    if not requirements:
        return 0.5  # Unknown requirements, don't filter out
    skills_lower = {s.lower() for s in skills}
    req_lower = {r.lower() for r in requirements}
    if not req_lower:
        return 0.5
    overlap = len(skills_lower & req_lower)
    return overlap / len(req_lower)


def _parse_reqs(job: Job) -> list[str]:
    if isinstance(job.requirements, list):
        return job.requirements
    try:
        return json.loads(job.requirements or "[]")
    except (json.JSONDecodeError, TypeError):
        return []


def score_single_job(db: Session, profile: UserProfile, job: Job) -> dict:
    """Score a single job against the user's CV."""
    reqs = _parse_reqs(job)
    # Pre-filter: if keyword overlap < 20%, mark as low match without LLM
    overlap = _keyword_overlap(profile.skills or [], reqs)
    if overlap < 0.2 and reqs:
        result = {
            "score": int(overlap * 100),
            "matches": [],
            "gaps": reqs[:5],
            "explanation": "Low keyword overlap - likely not a strong match.",
        }
        job.cv_score = result["score"]
        job.score_explanation = result["explanation"]
        job.score_details = json.dumps(result)
        db.commit()
        return result

    system = _load_prompt()
    prompt = (
        f"JOB REQUIREMENTS: {json.dumps(reqs)}\n"
        f"JOB TITLE: {job.title}\n"
        f"CANDIDATE SKILLS: {json.dumps(profile.skills or [])}\n"
        f"CANDIDATE EXPERIENCE PREVIEW/SUMMARY: {profile.experience_summary or 'Not provided'}\n"
        f"CANDIDATE DETAILED EXPERIENCE:\n{json.dumps(profile.structured_cv.get('experience_details', []), indent=2)}"
    )

    response = llm_call(db=db, prompt=prompt, task_type="score", system=system)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {"score": 50, "matches": [], "gaps": [], "explanation": "Could not parse score"}

    job.cv_score = result.get("score", 50)
    job.score_explanation = result.get("explanation", "")
    job.score_details = json.dumps(result)
    db.commit()
    return result


def score_batch(db: Session, profile: UserProfile, jobs: list[Job]) -> list[dict]:
    """Score multiple jobs in batches of 5 for token efficiency."""
    results = []
    batch_size = 5

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]

        # Filter out jobs that can be pre-scored without LLM
        llm_batch = []
        for job in batch:
            reqs = _parse_reqs(job)
            overlap = _keyword_overlap(profile.skills or [], reqs)
            if overlap < 0.2 and reqs:
                result = {
                    "score": int(overlap * 100),
                    "matches": [],
                    "gaps": reqs[:5],
                    "explanation": "Low keyword overlap.",
                }
                job.cv_score = result["score"]
                job.score_explanation = result["explanation"]
                job.score_details = json.dumps(result)
                results.append(result)
            else:
                llm_batch.append(job)

        if not llm_batch:
            continue

        if len(llm_batch) == 1:
            results.append(score_single_job(db, profile, llm_batch[0]))
            continue

        # Batch scoring: multiple jobs in one LLM call
        system = _load_prompt()
        jobs_text = ""
        for idx, job in enumerate(llm_batch):
            jobs_text += (
                f"\nJOB {idx + 1}: {job.title} at {job.company}\n"
                f"Requirements: {json.dumps(_parse_reqs(job))}\n"
            )

        prompt = (
            f"Score this candidate against {len(llm_batch)} jobs. "
            f"Return JSON array of scores.\n"
            f"CANDIDATE SKILLS: {json.dumps(profile.skills or [])}\n"
            f"CANDIDATE EXPERIENCE SUMMARY: {profile.experience_summary or 'Not provided'}\n"
            f"CANDIDATE DETAILED EXPERIENCE:\n{json.dumps(profile.structured_cv.get('experience_details', []), indent=2)}\n"
            f"{jobs_text}"
        )

        response = llm_call(db=db, prompt=prompt, task_type="score", system=system)

        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict) and "scores" in parsed:
                batch_results = parsed["scores"]
            elif isinstance(parsed, list):
                batch_results = parsed
            else:
                batch_results = [parsed]
        except json.JSONDecodeError:
            batch_results = [{"score": 50, "matches": [], "gaps": [], "explanation": "Parse error"}] * len(llm_batch)

        for j, job in enumerate(llm_batch):
            r = batch_results[j] if j < len(batch_results) else {"score": 50}
            job.cv_score = r.get("score", 50)
            job.score_explanation = r.get("explanation", "")
            job.score_details = json.dumps(r)
            results.append(r)

    db.commit()
    return results
