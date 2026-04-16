from __future__ import annotations

import os
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from services.llm_client import llm_call


def _load_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "extract_portfolio.txt")
    with open(path) as f:
        return f.read().strip()


def _extract_github_username(url: str) -> str | None:
    """Extract username from a GitHub profile URL."""
    match = re.match(r"https?://github\.com/([a-zA-Z0-9_-]+)/?$", url.strip())
    return match.group(1) if match else None


def _fetch_github_repos(username: str) -> str:
    """Fetch top repositories from GitHub API and format as text."""
    api_url = f"https://api.github.com/users/{username}/repos"
    params = {"sort": "updated", "per_page": 10, "type": "owner"}
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(api_url, params=params, headers=headers)
            if resp.status_code != 200:
                return ""
            repos = resp.json()
    except httpx.RequestError:
        return ""

    if not repos:
        return ""

    # Sort by stars then by recently updated; guard against null updated_at
    repos = sorted(
        repos,
        key=lambda r: (r.get("stargazers_count", 0), r.get("updated_at") or ""),
        reverse=True,
    )

    lines = []
    for repo in repos[:6]:
        name = repo.get("name", "")
        desc = repo.get("description", "") or "No description"
        lang = repo.get("language", "") or "Unknown"
        stars = repo.get("stargazers_count", 0)
        lines.append(f"Project: {name} | Language: {lang} | Stars: {stars} | Description: {desc}")

    return "\n".join(lines)


def _fetch_webpage(url: str) -> str:
    """Fetch and extract text content from a webpage."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return ""
            page_text = resp.text
    except httpx.RequestError:
        return ""

    soup = BeautifulSoup(page_text, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text[:3000]  # Truncate to save tokens


def fetch_portfolio(url: str) -> str:
    """Fetch portfolio content. Uses GitHub API for GitHub URLs, web scraping otherwise."""
    github_user = _extract_github_username(url)
    if github_user:
        return _fetch_github_repos(github_user)
    return _fetch_webpage(url)


def summarize_portfolio(db: Session, raw_content: str) -> str:
    """Use LLM to extract project summaries from portfolio content."""
    if not raw_content.strip():
        return ""

    system = _load_prompt()
    prompt = f"PORTFOLIO CONTENT:\n{raw_content[:3000]}"

    response = llm_call(
        db=db,
        prompt=prompt,
        task_type="onboard",
        system=system,
        cache_ttl=8760,
    )

    return response.strip()
