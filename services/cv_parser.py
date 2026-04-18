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
        (r"(?i)\b(summary|profile|objective|about\s*me|professional\s*summary)\b", "summary"),
        (r"(?i)\b(experiences?|work\s*history|employment|work\s*experience|professional\s*experience|career)\b", "experience"),
        (r"(?i)\b(education|academics?|qualifications?|academic\s*background)\b", "education"),
        (r"(?i)\b(skills?|technical\s*skills?|core\s*competenc|competenc|technologies|tech\s*stack|tools)\b", "skills"),
        (r"(?i)\b(projects?|portfolio|personal\s*projects?|side\s*projects?)\b", "projects"),
        (r"(?i)\b(certif|licens|credentials?|accreditations?)\b", "certifications"),
        (r"(?i)\b(languages?)\b", "languages"),
        (r"(?i)\b(awards?|honou?rs?|achievements?|accomplishments?)\b", "awards"),
        (r"(?i)\b(publications?|research|papers?)\b", "publications"),
        (r"(?i)\b(volunteer|community|extra-?curricular)\b", "volunteer"),
        (r"(?i)\b(interests?|hobbies)\b", "interests"),
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
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "kotlin", "swift", "scala", "r", "matlab", "perl",
        "dart", "objective-c", "lua", "haskell", "clojure", "elixir", "solidity",
        # Frontend frameworks
        "react", "react native", "angular", "vue", "vue.js", "next.js", "nuxt",
        "svelte", "ember", "jquery", "redux", "mobx", "zustand",
        # Backend frameworks
        "node.js", "express", "nestjs", "django", "flask", "fastapi", "spring",
        "spring boot", "rails", "laravel", ".net", "asp.net", "gin", "fiber",
        # Databases
        "sql", "postgresql", "mysql", "mariadb", "sqlite", "oracle", "sql server",
        "mongodb", "dynamodb", "cassandra", "redis", "elasticsearch", "neo4j",
        "snowflake", "bigquery", "redshift", "databricks", "clickhouse",
        # Cloud / DevOps
        "aws", "azure", "gcp", "google cloud", "digitalocean", "heroku",
        "docker", "kubernetes", "k8s", "terraform", "ansible", "pulumi",
        "helm", "istio", "prometheus", "grafana", "datadog", "new relic",
        # CI/CD
        "git", "github", "gitlab", "bitbucket", "ci/cd", "jenkins",
        "github actions", "circleci", "travis", "argocd",
        # ML / Data
        "machine learning", "deep learning", "nlp", "llm", "generative ai",
        "computer vision", "reinforcement learning", "mlops",
        "tensorflow", "pytorch", "keras", "scikit-learn", "xgboost", "lightgbm",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "hugging face", "langchain", "openai", "anthropic",
        "spark", "hadoop", "kafka", "airflow", "dbt", "fivetran",
        # Frontend
        "html", "html5", "css", "css3", "sass", "scss", "less", "tailwind",
        "bootstrap", "material ui", "chakra ui", "styled components",
        # APIs / Architecture
        "rest api", "graphql", "grpc", "soap", "websocket", "microservices",
        "event-driven", "serverless", "lambda", "api gateway",
        # Agile / PM
        "agile", "scrum", "kanban", "jira", "confluence", "asana", "trello",
        "notion", "linear",
        # OS / Scripting
        "linux", "unix", "macos", "windows", "bash", "shell scripting",
        "powershell", "zsh",
        # Data
        "data analysis", "data engineering", "data science", "etl", "elt",
        "tableau", "power bi", "looker", "metabase", "superset",
        # Design
        "figma", "sketch", "adobe xd", "photoshop", "illustrator",
        "invision", "ui/ux", "user research", "wireframing", "prototyping",
        # PM / soft
        "product management", "product strategy", "roadmapping", "project management",
        "stakeholder management", "a/b testing", "user research",
        "communication", "leadership", "teamwork", "mentoring", "problem solving",
        "critical thinking", "analytical",
        # Testing
        "unit testing", "integration testing", "jest", "pytest", "cypress",
        "selenium", "playwright", "junit", "mocha", "chai",
        # Security
        "cybersecurity", "penetration testing", "owasp", "oauth", "jwt",
        "encryption", "tls", "ssl",
        # Business / Sales / Marketing
        "seo", "sem", "google analytics", "hubspot", "salesforce", "marketo",
        "digital marketing", "content marketing", "brand management",
        "sales strategy", "crm", "b2b", "b2c",
        # Finance
        "financial modeling", "excel", "vba", "bloomberg", "quickbooks",
    ]
    text_lower = text.lower()
    found = []
    for s in known_skills:
        if s in text_lower and s not in found:
            found.append(s)
    return found
