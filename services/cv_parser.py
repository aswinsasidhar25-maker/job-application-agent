from __future__ import annotations

import os
import re


def extract_text_from_pdf(file_path: str) -> str:
    import fitz  # pymupdf

    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return text.strip()


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif ext == ".txt":
        with open(file_path, "r") as f:
            return f.read().strip()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def extract_sections(text: str) -> dict[str, str]:
    """Rule-based section extraction from CV text. Zero LLM tokens."""
    section_patterns = [
        (r"(?i)\b(summary|profile|objective|about)\b", "summary"),
        (r"(?i)\b(experiences?|work\s*history|employment)\b", "experience"),
        (r"(?i)\b(education|academics?|qualifications?)\b", "education"),
        (r"(?i)\b(skills?|technical|competenc|technologies)\b", "skills"),
        (r"(?i)\b(projects?|portfolio)\b", "projects"),
        (r"(?i)\b(certif|licens|credentials?)\b", "certifications"),
    ]

    lines = text.split("\n")
    sections: dict[str, list[str]] = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched = False
        for pattern, section_name in section_patterns:
            if re.search(pattern, stripped) and len(stripped) < 60:
                current_section = section_name
                sections.setdefault(current_section, [])
                matched = True
                break

        if not matched:
            sections.setdefault(current_section, [])
            sections[current_section].append(stripped)

    return {k: "\n".join(v) for k, v in sections.items() if v}


def extract_skills_keywords(text: str) -> list[str]:
    """Extract skills using keyword matching. Zero LLM tokens."""
    known_skills = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "git", "ci/cd", "jenkins", "github actions",
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "html", "css", "sass", "tailwind", "bootstrap",
        "rest api", "graphql", "grpc", "microservices",
        "agile", "scrum", "jira", "confluence",
        "linux", "bash", "shell scripting",
        "data analysis", "data engineering", "etl",
        "figma", "sketch", "ui/ux",
        "product management", "project management",
        "communication", "leadership", "teamwork",
    ]
    text_lower = text.lower()
    return [s for s in known_skills if s in text_lower]
