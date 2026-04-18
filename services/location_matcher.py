from __future__ import annotations

import re


_REMOTE_TOKENS = {
    "remote", "anywhere", "worldwide", "global", "work from home", "wfh",
    "fully remote", "remote-first", "any", "",
}


COUNTRY_ALIASES: dict[str, set[str]] = {
    "india": {
        "india", "in", "bharat",
        "bengaluru", "bangalore", "mumbai", "bombay", "delhi", "new delhi",
        "hyderabad", "chennai", "madras", "kolkata", "calcutta", "pune",
        "ahmedabad", "jaipur", "noida", "gurgaon", "gurugram", "kochi",
        "trivandrum", "thiruvananthapuram", "indore", "lucknow", "chandigarh",
        "jalandhar", "ludhiana", "amritsar", "nagpur", "bhubaneswar",
        "coimbatore", "mysore", "mysuru", "vadodara", "visakhapatnam",
    },
    "usa": {
        "usa", "us", "u.s.", "u.s.a.", "united states", "united states of america",
        "america", "new york", "nyc", "san francisco", "sf", "los angeles", "la",
        "seattle", "boston", "chicago", "austin", "washington", "dc",
        "atlanta", "denver", "miami", "dallas", "houston", "philadelphia",
        "portland", "san diego", "san jose", "silicon valley",
    },
    "uk": {
        "uk", "u.k.", "united kingdom", "britain", "great britain", "england",
        "london", "manchester", "edinburgh", "birmingham", "glasgow", "bristol",
        "cambridge", "oxford", "leeds",
    },
    "canada": {
        "canada", "ca", "toronto", "vancouver", "montreal", "ottawa", "calgary",
        "edmonton", "waterloo",
    },
    "germany": {
        "germany", "de", "deutschland", "berlin", "munich", "muenchen",
        "hamburg", "frankfurt", "cologne", "koeln", "stuttgart",
    },
    "australia": {
        "australia", "au", "sydney", "melbourne", "brisbane", "perth",
    },
    "singapore": {"singapore", "sg"},
    "ireland": {"ireland", "ie", "dublin"},
    "netherlands": {"netherlands", "nl", "amsterdam", "rotterdam", "utrecht"},
    "france": {"france", "fr", "paris", "lyon", "marseille"},
    "uae": {"uae", "dubai", "abu dhabi", "united arab emirates"},
}


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[.,;|/\\()\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if t}


def is_remote_location(location: str) -> bool:
    norm = _normalize(location)
    if not norm:
        return True
    return any(token in norm for token in _REMOTE_TOKENS if token)


def _country_of(location: str) -> str | None:
    """Map a location to a canonical country key, if identifiable."""
    norm = _normalize(location)
    if not norm:
        return None
    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if not alias:
                continue
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, norm):
                return country
    return None


def location_matches(user_location: str, job_location: str, remote_preference: str = "any") -> bool:
    """Check whether a job's location satisfies the user's requested location.

    Rules:
    - Empty user_location -> always match.
    - Remote-ish job ("worldwide"/"anywhere"/"remote") matches unless user wants onsite only.
    - If either side maps to a known country, both must map to the same country.
    - Else, fall back to substring/token overlap between the two.
    """
    if not user_location or not user_location.strip():
        return True

    job_norm = _normalize(job_location)
    user_norm = _normalize(user_location)

    if is_remote_location(job_location):
        if remote_preference == "onsite":
            return False
        return True

    user_country = _country_of(user_location)
    job_country = _country_of(job_location)

    if user_country and job_country:
        return user_country == job_country

    if user_country and not job_country:
        return False
    if job_country and not user_country:
        return False

    user_toks = _tokens(user_location)
    job_toks = _tokens(job_location)
    if user_toks & job_toks:
        return True
    if user_norm in job_norm or job_norm in user_norm:
        return True
    return False
