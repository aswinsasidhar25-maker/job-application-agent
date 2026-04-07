import re
import httpx
from bs4 import BeautifulSoup
from services.job_sources.base import JobSource, JobResult


class WebScraperSource(JobSource):
    """Fallback scraper using Google search results. Use sparingly."""
    name = "scraper"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        search_query = f"{query} jobs {location}".strip()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.google.com/search",
                params={"q": search_query, "num": 10},
                headers=headers,
            )
            if resp.status_code != 200:
                return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for result in soup.select("div.g"):
            title_el = result.select_one("h3")
            link_el = result.select_one("a")
            snippet_el = result.select_one("div.VwiC3b")

            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            url = link_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            if not any(kw in title.lower() for kw in ["job", "hiring", "career", "position", "opening"]):
                continue

            company = ""
            company_match = re.search(r"at\s+(.+?)(?:\s*[-|]|\s*$)", title)
            if company_match:
                company = company_match.group(1).strip()

            jobs.append(JobResult(
                external_id=f"scraper-{hash(url)}",
                source=self.name,
                title=title,
                company=company,
                location=location,
                description=snippet,
                url=url,
            ))

        return jobs[:kwargs.get("num", 10)]
