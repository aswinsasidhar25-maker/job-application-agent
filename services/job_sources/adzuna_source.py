import httpx
from config import settings
from services.job_sources.base import JobSource, JobResult


class AdzunaSource(JobSource):
    name = "adzuna"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            return []

        country = kwargs.get("country", "us")
        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "what": query,
            "results_per_page": kwargs.get("num", 20),
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()

        jobs = []
        for item in data.get("results", []):
            jobs.append(JobResult(
                external_id=str(item.get("id", "")),
                source=self.name,
                title=item.get("title", ""),
                company=item.get("company", {}).get("display_name", ""),
                location=item.get("location", {}).get("display_name", ""),
                salary_min=item.get("salary_min"),
                salary_max=item.get("salary_max"),
                description=item.get("description", ""),
                url=item.get("redirect_url", ""),
                posted_date=item.get("created", ""),
            ))
        return jobs
