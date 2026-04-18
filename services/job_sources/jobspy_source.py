from __future__ import annotations

from config import settings
from services.job_sources.base import JobSource, JobResult


class JobSpySource(JobSource):
    """Scrapes LinkedIn, Indeed, Glassdoor without API keys using python-jobspy."""
    name = "jobspy"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        try:
            from jobspy import scrape_jobs
            import pandas as pd
        except ImportError:
            return []

        try:
            df = scrape_jobs(
                site_name=["linkedin", "indeed", "glassdoor"],
                search_term=query,
                location=location or "Worldwide",
                results_wanted=kwargs.get("num", settings.JOBSPY_RESULTS_PER_SITE),
                hours_old=72,
                country_indeed="india" if "india" in (location or "").lower() else "usa",
            )
        except Exception:
            return []

        if df is None or df.empty:
            return []

        jobs = []
        for _, row in df.iterrows():
            def safe(val):
                return str(val) if val and str(val) != "nan" else ""

            salary_min = None
            salary_max = None
            try:
                if row.get("min_amount") and str(row["min_amount"]) != "nan":
                    salary_min = float(row["min_amount"])
                if row.get("max_amount") and str(row["max_amount"]) != "nan":
                    salary_max = float(row["max_amount"])
            except (ValueError, TypeError):
                pass

            jobs.append(JobResult(
                external_id=safe(row.get("id")) or f"jobspy-{hash(safe(row.get('job_url', '')))}",
                source=f"jobspy-{safe(row.get('site', 'unknown'))}",
                title=safe(row.get("title")),
                company=safe(row.get("company")),
                location=safe(row.get("location")),
                remote_type="remote" if row.get("is_remote") else "onsite",
                salary_min=salary_min,
                salary_max=salary_max,
                description=safe(row.get("description")),
                url=safe(row.get("job_url")),
                posted_date=safe(row.get("date_posted")),
                requirements=[],
            ))

        return jobs
