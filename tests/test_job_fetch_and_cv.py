"""
Integration tests for:
  1. Job fetching (JobSpy + other sources)
  2. Job summarization via LLM
  3. CV scoring against a job
  4. CV rewriting via full model

Run from project root:
  python -m pytest tests/test_job_fetch_and_cv.py -v -s
Or directly:
  python tests/test_job_fetch_and_cv.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# Make sure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db

SEPARATOR = "=" * 60


def section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


# ──────────────────────────────────────────────────────────────
# TEST 1: JobSpy can fetch jobs
# ──────────────────────────────────────────────────────────────
def test_jobspy_fetch():
    section("TEST 1: JobSpy – fetching jobs from LinkedIn/Indeed/Glassdoor")
    from services.job_sources.jobspy_source import JobSpySource

    source = JobSpySource()
    results = asyncio.run(source.search("software engineer", "Remote"))

    if not results:
        print("  ⚠️  No results returned. This could mean scraping was blocked or jobspy is not installed.")
    else:
        print(f"  ✅  Fetched {len(results)} jobs from JobSpy")
        for job in results[:3]:
            print(f"      [{job.source}] {job.title} @ {job.company} | {job.location}")
            print(f"       URL: {job.url}")

    return results


# ──────────────────────────────────────────────────────────────
# TEST 2: LLM can summarize a job description
# ──────────────────────────────────────────────────────────────
def test_job_summarization():
    section("TEST 2: LLM – Summarize a sample job description")
    from agents.job_search import _summarize_job

    sample_desc = """
    We are looking for a Senior Python Engineer to join our platform team.
    You will design scalable microservices, work with PostgreSQL and Redis,
    deploy on AWS using Kubernetes, and mentor junior engineers.
    Requirements: 5+ years Python, REST APIs, Docker, CI/CD pipelines.
    Nice to have: FastAPI, Celery, GraphQL.
    """

    db = SessionLocal()
    try:
        result = _summarize_job(db, sample_desc)
        print(f"  ✅  Summarization result:")
        print(f"      Summary: {result.get('summary', 'N/A')}")
        print(f"      Requirements: {result.get('requirements', [])}")
        assert "summary" in result, "❌ 'summary' key missing from LLM response"
        assert "requirements" in result, "❌ 'requirements' key missing from LLM response"
        return result
    except Exception as e:
        print(f"  ❌  Summarization failed: {e}")
        return {}
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# TEST 3: CV scoring against a stored job
# ──────────────────────────────────────────────────────────────
def test_cv_scoring():
    section("TEST 3: CV Scoring – Score CV against a job in the DB")
    from agents.orchestrator import get_profile, get_jobs, has_cv
    from agents.cv_scorer import score_single_job

    db = SessionLocal()
    try:
        profile = get_profile(db)
        if not profile:
            print("  ⚠️  No user profile found. Complete onboarding first.")
            return

        if not has_cv(db):
            print("  ⚠️  No CV uploaded. Upload a CV via Onboarding.")
            return

        jobs = get_jobs(db)
        if not jobs:
            print("  ⚠️  No jobs in DB. Run job search first.")
            return

        job = jobs[0]
        print(f"  Scoring CV against: {job.title} @ {job.company}")
        result = score_single_job(db, profile, job)

        score = result.get("score", "N/A")
        print(f"  ✅  Score: {score}%")
        print(f"      Explanation: {result.get('explanation', 'N/A')}")
        print(f"      Matches: {result.get('matches', [])[:3]}")
        print(f"      Gaps:    {result.get('gaps', [])[:3]}")
        return result
    except Exception as e:
        print(f"  ❌  CV scoring failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# TEST 4: CV rewriting for a job
# ──────────────────────────────────────────────────────────────
def test_cv_rewriting():
    section("TEST 4: CV Rewriting – Rewrite CV tailored to a job")
    from agents.orchestrator import get_profile, get_jobs, has_cv
    from agents.cv_rewriter import rewrite_cv_for_job

    db = SessionLocal()
    try:
        profile = get_profile(db)
        if not profile or not profile.parsed_cv_text:
            print("  ⚠️  No CV found. Upload via Onboarding page.")
            return

        jobs = get_jobs(db)
        if not jobs:
            print("  ⚠️  No jobs in DB to rewrite CV for.")
            return

        job = jobs[0]
        print(f"  Rewriting CV for: {job.title} @ {job.company}")
        print(f"  Using model: {os.getenv('FULL_MODEL', 'ollama/llama3.2')}")

        rewritten = rewrite_cv_for_job(db, profile, job)

        if rewritten:
            print(f"  ✅  CV rewritten! ({len(rewritten)} chars)")
            print(f"      Saved to: {job.rewritten_cv_path}")
            print("\n  --- First 500 chars of rewritten CV ---")
            print(rewritten[:500])
            print("  ...")
        else:
            print("  ❌  Rewrite returned empty response")
        return rewritten
    except Exception as e:
        print(f"  ❌  CV rewriting failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# TEST 5: Full search_jobs pipeline (end-to-end, small batch)
# ──────────────────────────────────────────────────────────────
def test_full_search_pipeline():
    section("TEST 5: Full search_jobs pipeline (1 query, max 3 results)")
    from agents.orchestrator import get_profile
    from agents.job_search import search_jobs

    db = SessionLocal()
    try:
        profile = get_profile(db)
        if not profile:
            print("  ⚠️  Complete onboarding first to set up a profile.")
            return

        # Override JOBSPY_RESULTS_PER_SITE to keep the test fast
        import config
        config.settings.JOBSPY_RESULTS_PER_SITE = 3

        new_jobs = search_jobs(db, profile, custom_query="product manager", custom_location="Remote")
        if new_jobs:
            print(f"  ✅  Added {len(new_jobs)} new job(s) to DB:")
            for j in new_jobs:
                print(f"      [{j.source}] {j.title} @ {j.company} | {j.location}")
        else:
            print("  ℹ️  No new jobs found (they may already exist in DB or scraping was blocked).")
        return new_jobs
    except Exception as e:
        print(f"  ❌  Full pipeline failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
def print_db_summary():
    section("DB SUMMARY")
    from models.job import Job
    from models.user import UserProfile
    from models.cache import TokenUsage

    db = SessionLocal()
    try:
        jobs_total = db.query(Job).count()
        jobs_with_score = db.query(Job).filter(Job.cv_score.isnot(None)).count()
        jobs_with_rewrite = db.query(Job).filter(Job.rewritten_cv_path.isnot(None)).count()
        profile = db.query(UserProfile).first()
        usages = db.query(TokenUsage).all()
        total_cost = sum(u.cost_usd for u in usages)

        print(f"  Profile:          {'✅ Exists (' + (profile.name or 'unnamed') + ')' if profile else '❌ Not set up'}")
        print(f"  CV uploaded:      {'✅' if profile and profile.parsed_cv_text else '❌'}")
        print(f"  Total jobs in DB: {jobs_total}")
        print(f"  Scored jobs:      {jobs_with_score}")
        print(f"  Rewritten CVs:    {jobs_with_rewrite}")
        print(f"  Total LLM cost:   ${total_cost:.4f} USD")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

    args = sys.argv[1:]
    run_all = not args

    if run_all or "fetch" in args:
        test_jobspy_fetch()

    if run_all or "summarize" in args:
        test_job_summarization()

    if run_all or "score" in args:
        test_cv_scoring()

    if run_all or "rewrite" in args:
        test_cv_rewriting()

    if run_all or "pipeline" in args:
        test_full_search_pipeline()

    print_db_summary()
    print(f"\n{SEPARATOR}")
    print("  All tests complete.")
    print(SEPARATOR)
