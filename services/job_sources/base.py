from dataclasses import dataclass, field


@dataclass
class JobResult:
    external_id: str = ""
    source: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    remote_type: str = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    description: str = ""
    url: str = ""
    posted_date: str = ""
    requirements: list[str] = field(default_factory=list)


class JobSource:
    name: str = "base"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        raise NotImplementedError
