from __future__ import annotations

import asyncio
import json
import os
import re
import time
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from services.llm_client import llm_call
from services.job_sources.base import JobResult
from services.job_sources.serpapi_source import SerpAPISource
from services.job_sources.adzuna_source import AdzunaSource
from services.job_sources.remotive_source import RemotiveSource
from services.job_sources.scraper import WebScraperSource
from models.job import Job
from models.user import UserProfile


def _load_prompt():
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "summarize_job.txt")
    with open(path) as f:
        return f.read().strip()


def _build_queries(profile: UserProfile) -> list[dict]:
    """Build search queries from user preferences. No LLM needed."""
    queries = []
    roles = profile.preferred_roles or ["software engineer"]
    locations = profile.preferred_locations or [""]

    for role in roles:
        for loc in locations:
            queries.append({"query": role, "location": loc})
    return queries


def _is_duplicate(new_job: JobResult, existing_jobs: list[Job]) -> bool:
    """Check for duplicates using fuzzy string matching. No LLM needed."""
    for existing in existing_jobs:
        title_score = fuzz.ratio(new_job.title.lower(), existing.title.lower())
        company_score = fuzz.ratio(new_job.company.lower(), existing.company.lower())
        if title_score > 85 and company_score > 80:
            return True
    return existing_jobs and any(
        new_job.external_id and new_job.external_id == e.external_id
        for e in existing_jobs
    )


def _strip_html(text: str) -> str:
    """Remove HTML tags from description."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


async def _fetch_from_all_sources(query: str, location: str) -> list[JobResult]:
    """Fetch from all configured sources in parallel."""
    sources = [SerpAPISource(), AdzunaSource(), RemotiveSource(), WebScraperSource()]
    tasks = [source.search(query, location) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)
    return all_jobs


def _summarize_job(db: Session, description: str) -> dict:
    """Summarize a job description using mini model. ~300 tokens."""
    if not description or len(description) < 50:
        return {"summary": description, "requirements": []}

    system = _load_prompt()
    # Truncate description to save tokens
    truncated = description[:2000]
    prompt = f"JOB DESCRIPTION:\n{truncated}"

    response = llm_call(
        db=db,
        prompt=prompt,
        task_type="summarize",
        system=system,
        cache_ttl=168,  # 7 days
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"summary": description[:500], "requirements": []}


def search_jobs(db: Session, profile: UserProfile, custom_query: str = "", custom_location: str = "") -> list[Job]:
    """Main job search function. Orchestrates search, dedup, and summarization."""
    if custom_query:
        queries = [{"query": custom_query, "location": custom_location}]
    else:
        queries = _build_queries(profile)

    existing_jobs = db.query(Job).all()
    new_jobs = []

    for q in queries:
        raw_results = asyncio.run(
            _fetch_from_all_sources(q["query"], q["location"])
        )

        for result in raw_results:
            if _is_duplicate(result, existing_jobs + new_jobs_as_models(new_jobs)):
                continue

            # Clean description
            clean_desc = _strip_html(result.description)

            # Summarize with mini model (4s delay keeps us under Gemini free tier 15 RPM)
            time.sleep(4)
            summary_data = _summarize_job(db, clean_desc)

            job = Job(
                external_id=result.external_id,
                source=result.source,
                title=result.title,
                company=result.company,
                location=result.location,
                remote_type=result.remote_type,
                salary_min=result.salary_min,
                salary_max=result.salary_max,
                description_raw=clean_desc,
                description_summary=summary_data.get("summary", ""),
                requirements=summary_data.get("requirements", result.requirements),
                url=result.url,
                posted_date=result.posted_date,
                status="new",
            )
            db.add(job)
            new_jobs.append(job)

    db.commit()
    return new_jobs


def new_jobs_as_models(jobs: list[Job]) -> list[Job]:
    """Helper to treat uncommitted Job objects as existing for dedup."""
    return jobs
