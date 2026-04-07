import json
import os
from sqlalchemy.orm import Session
from services.llm_client import llm_call
from services.cv_parser import extract_text, extract_sections, extract_skills_keywords
from models.user import UserProfile
from config import settings


def _load_prompt():
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", "extract_profile.txt")
    with open(path) as f:
        return f.read().strip()


def save_cv_file(uploaded_file_bytes: bytes, filename: str) -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file_bytes)
    return path


def process_cv(db: Session, file_path: str) -> dict:
    """Parse CV and extract structured data. One LLM call for structuring."""
    raw_text = extract_text(file_path)
    sections = extract_sections(raw_text)
    keyword_skills = extract_skills_keywords(raw_text)

    # Single mini-model call to extract structured profile
    system = _load_prompt()
    prompt = f"CV TEXT:\n{raw_text[:3000]}"  # Truncate to save tokens

    response = llm_call(
        db=db,
        prompt=prompt,
        task_type="onboard",
        system=system,
        cache_ttl=8760,  # 1 year - CV doesn't change often
    )

    try:
        structured = json.loads(response)
    except json.JSONDecodeError:
        structured = {}

    # Merge LLM-extracted skills with keyword-extracted skills (dedup)
    llm_skills = structured.get("skills", [])
    all_skills = list(set(llm_skills + keyword_skills))
    structured["skills"] = all_skills

    return {
        "parsed_cv_text": raw_text,
        "sections": sections,
        "structured_cv": structured,
        "skills": all_skills,
    }


def save_profile(
    db: Session,
    name: str = "",
    email: str = "",
    phone: str = "",
    location: str = "",
    preferred_roles: list[str] | None = None,
    preferred_locations: list[str] | None = None,
    remote_preference: str = "any",
    min_salary: float | None = None,
    projects_summary: str = "",
    cv_data: dict | None = None,
    raw_cv_path: str = "",
) -> UserProfile:
    """Save or update user profile."""
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)

    profile.name = name or profile.name
    profile.email = email or profile.email
    profile.phone = phone or profile.phone
    profile.location = location or profile.location
    profile.preferred_roles = preferred_roles or profile.preferred_roles or []
    profile.preferred_locations = preferred_locations or profile.preferred_locations or []
    profile.remote_preference = remote_preference or profile.remote_preference
    profile.min_salary = min_salary if min_salary is not None else profile.min_salary
    profile.projects_summary = projects_summary or profile.projects_summary
    profile.raw_cv_path = raw_cv_path or profile.raw_cv_path

    if cv_data:
        profile.parsed_cv_text = cv_data.get("parsed_cv_text", profile.parsed_cv_text)
        profile.structured_cv = cv_data.get("structured_cv", profile.structured_cv)
        profile.skills = cv_data.get("skills", profile.skills)
        profile.experience_summary = cv_data.get("structured_cv", {}).get(
            "experience_summary", profile.experience_summary
        )

    db.commit()
    db.refresh(profile)
    return profile
