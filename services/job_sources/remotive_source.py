import httpx
from services.job_sources.base import JobSource, JobResult


class RemotiveSource(JobSource):
    name = "remotive"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        params = {"search": query, "limit": kwargs.get("num", 20)}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://remotive.com/api/remote-jobs", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()

        jobs = []
        for item in data.get("jobs", []):
            tags = item.get("tags", [])
            jobs.append(JobResult(
                external_id=str(item.get("id", "")),
                source=self.name,
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Worldwide"),
                remote_type="remote",
                description=item.get("description", ""),
                url=item.get("url", ""),
                posted_date=item.get("publication_date", ""),
                requirements=tags if isinstance(tags, list) else [],
            ))
        return jobs
