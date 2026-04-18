import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")

    MINI_MODEL: str = os.getenv("MINI_MODEL", "gpt-4o-mini")
    FULL_MODEL: str = os.getenv("FULL_MODEL", "gpt-4o")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # JobSpy scraper config
    JOBSPY_RESULTS_PER_SITE: int = int(os.getenv("JOBSPY_RESULTS_PER_SITE", "15"))

    MONTHLY_TOKEN_BUDGET: float = float(os.getenv("MONTHLY_TOKEN_BUDGET", "10.0"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/app.db")

    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "data", "uploads")
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "data", "app.db")


settings = Settings()
