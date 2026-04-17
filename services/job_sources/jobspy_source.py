from __future__ import annotations

import hashlib
from services.job_sources.base import JobResult


def fetch_jobspy(
    search_term: str,
    location: str = "",
    site_name: list[str] | None = None,
    results_wanted: int = 10,
    job_type: str | None = None,
) -> list[JobResult]:
    """Scrape jobs using python-jobspy. Returns list of JobResult."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return []

    if not site_name:
        site_name = ["indeed", "linkedin", "glassdoor"]

    kwargs = {
        "site_name": site_name,
        "search_term": search_term,
        "results_wanted": results_wanted,
        "hours_old": 72,
        "country_indeed": "India",
    }
    if location:
        kwargs["location"] = location
    if job_type:
        kwargs["job_type"] = job_type

    try:
        df = scrape_jobs(**kwargs)
    except Exception:
        return []

    if df is None or df.empty:
        return []

    jobs = []
    for _, row in df.iterrows():
        url = str(row.get("job_url", "") or "")
        ext_id = f"{row.get('site', 'unknown')}-{hashlib.md5(url.encode()).hexdigest()[:12]}"

        salary_min = None
        salary_max = None
        try:
            val = row.get("min_amount")
            if val is not None and str(val) not in ("", "nan", "None"):
                salary_min = float(val)
        except (ValueError, TypeError):
            pass
        try:
            val = row.get("max_amount")
            if val is not None and str(val) not in ("", "nan", "None"):
                salary_max = float(val)
        except (ValueError, TypeError):
            pass

        title = str(row.get("title", "") or "")
        company = str(row.get("company_name", "") or row.get("company", "") or "")
        loc = str(row.get("location", "") or "")
        desc = str(row.get("description", "") or "")
        site = str(row.get("site", "") or "")
        raw_posted = row.get("date_posted")
        posted = "" if raw_posted is None or str(raw_posted) in ("NaT", "None", "nan", "") else str(raw_posted)[:10]

        remote_type = "unknown"
        if row.get("is_remote"):
            remote_type = "remote"

        if not title:
            continue

        jobs.append(JobResult(
            external_id=ext_id,
            source=site,
            title=title,
            company=company,
            location=loc,
            remote_type=remote_type,
            salary_min=salary_min,
            salary_max=salary_max,
            description=desc,
            url=url,
            posted_date=posted,
        ))

    return jobs
