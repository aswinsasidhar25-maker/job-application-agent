from __future__ import annotations

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
