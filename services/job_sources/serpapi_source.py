import httpx
from config import settings
from services.job_sources.base import JobSource, JobResult


class SerpAPISource(JobSource):
    name = "serpapi"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        if not settings.SERPAPI_API_KEY:
            return []

        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": settings.SERPAPI_API_KEY,
            "num": kwargs.get("num", 20),
        }
        if location:
            params["location"] = location

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()

        jobs = []
        for item in data.get("jobs_results", []):
            salary = item.get("detected_extensions", {})
            jobs.append(JobResult(
                external_id=item.get("job_id", ""),
                source=self.name,
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("location", ""),
                remote_type="remote" if "remote" in item.get("location", "").lower() else "unknown",
                salary_min=salary.get("salary_min"),
                salary_max=salary.get("salary_max"),
                description=item.get("description", ""),
                url=item.get("share_link", item.get("related_links", [{}])[0].get("link", "") if item.get("related_links") else ""),
                posted_date=item.get("detected_extensions", {}).get("posted_at", ""),
            ))
        return jobs
