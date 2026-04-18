# Job Search Agent Dashboard

> **For AI Agents & Developers**: This README is intentionally comprehensive. Every file, design pattern, data flow, database schema, API contract, and known quirk is documented below. Read this before making any changes to the codebase.

> **⚡ Active Runtime Stack**: This project currently runs on **Ollama (local LLMs)** with **`ollama/llama3.2`** as both MINI and FULL model. Job discovery is powered primarily by **JobSpy** (no API key required — scrapes LinkedIn, Indeed, Glassdoor). Monthly token budget is set to **unlimited (`0`)** since Ollama is free. See [Active Configuration](#active-configuration) for exact values.

An AI-powered job search dashboard built with **Streamlit** + **SQLAlchemy** + **litellm** + **Ollama**. It searches for jobs across multiple sources (primarily via JobSpy — no API keys needed), scores your CV against each opening using a local LLM, and rewrites your CV for maximum conversion — all running **100% locally, zero API cost**.

---

## Table of Contents

- [Core Philosophy](#core-philosophy)
- [Quick Start](#quick-start)
  - [Ollama Setup (Primary)](#ollama-setup-primary)
  - [Cloud LLM Setup (Alternative)](#cloud-llm-setup-alternative)
- [Active Configuration](#active-configuration)
- [Configuration Reference](#configuration-reference)
- [Architecture Overview](#architecture-overview)
- [Complete File Reference](#complete-file-reference)
  - [Entry Point](#entry-point)
  - [Config](#config)
  - [Database Layer](#database-layer)
  - [ORM Models](#orm-models)
  - [Agents](#agents)
  - [Services](#services)
  - [Job Sources](#job-sources)
  - [Prompt Templates](#prompt-templates)
  - [Pages (Streamlit UI)](#pages-streamlit-ui)
- [JobSpy — Primary Job Source](#jobspy--primary-job-source)
- [Data Flow Walkthroughs](#data-flow-walkthroughs)
- [Database Schema](#database-schema)
- [LLM Strategy & Token Optimization](#llm-strategy--token-optimization)
- [Job Sources Reference](#job-sources-reference)
- [Known Quirks & Gotchas](#known-quirks--gotchas)
- [Troubleshooting](#troubleshooting)
- [Extending the Codebase](#extending-the-codebase)

---

## Core Philosophy

This app is engineered around **4 inviolable principles** (do not break these when adding features):

1. **No autonomous agent loop.** The orchestrator (`agents/orchestrator.py`) is **pure Python dispatch logic** — it never calls an LLM. Every LLM call is triggered by a deliberate user action. This is the single biggest token cost saver vs. an agentic loop.

2. **Rule-based first, LLM last.** CV text extraction (PDF/DOCX), skill detection, job deduplication, and keyword pre-filtering are all done with Python/regex/rapidfuzz. LLMs are only invoked when heuristics won't suffice.

3. **Model tiering.** A cheap "mini" model (Haiku / GPT-4o-mini / Gemini Flash) handles 95%+ of all LLM calls. The expensive "full" model (Sonnet / GPT-4o / Gemini Pro) is reserved exclusively for CV rewriting and only called on explicit user request.

4. **Cache everything.** Every LLM response is stored in SQLite keyed by `SHA256(model + full_prompt)`. Identical requests cost zero tokens and return instantly.

---

## Quick Start

### Prerequisites

- Python 3.10+
- **Primary (used in this project):** Local [Ollama](https://ollama.com) install with `llama3.2` pulled
- **Alternative:** At least one cloud LLM API key (OpenAI, Anthropic, or Google Gemini)
- No job board API keys required — JobSpy scrapes LinkedIn, Indeed, and Glassdoor for free

### Installation

```bash
git clone https://github.com/aswinsasidhar25-maker/job-application-agent.git
cd job-application-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — see sections below

streamlit run app.py
```

Dashboard opens at `http://localhost:8501`.

---

### Ollama Setup (Primary)

This is the current active setup. Runs entirely locally — no API costs, no rate limits.

**Step 1 — Install Ollama:**
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

**Step 2 — Pull the model:**
```bash
ollama pull llama3.2        # ~2GB, good balance of speed and quality
# OR for lower RAM machines:
ollama pull phi3:mini       # ~1.8GB, faster on MacBook Air
ollama pull gemma2:2b       # ~1.6GB, very low RAM
```

**Step 3 — Start the Ollama server:**
```bash
ollama serve
# Runs at http://localhost:11434 by default
```

**Step 4 — Set `.env`:**
```env
MINI_MODEL=ollama/llama3.2
FULL_MODEL=ollama/llama3.2
OLLAMA_BASE_URL=http://localhost:11434
MONTHLY_TOKEN_BUDGET=0          # 0 = unlimited (Ollama is free)
JOBSPY_RESULTS_PER_SITE=10      # results per site from JobSpy
```

> **Model note:** Both `MINI_MODEL` and `FULL_MODEL` are currently set to `ollama/llama3.2`. For better CV rewrites, consider using a larger model for `FULL_MODEL` (e.g., `ollama/llama3.1:8b`) if your machine has enough RAM.

> **Ollama + JSON mode:** litellm cannot use `response_format={"type":"json_object"}` with Ollama. Instead, the `llm_client.py` appends `"Respond with valid JSON only. No explanation."` to the prompt automatically when `json_mode=True` and the model starts with `ollama/`.

---

### Cloud LLM Setup (Alternative)

Use this if you prefer hosted models without running Ollama locally.

```env
# OpenAI
OPENAI_API_KEY=sk-...
MINI_MODEL=gpt-4o-mini
FULL_MODEL=gpt-4o
MONTHLY_TOKEN_BUDGET=10.0

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
MINI_MODEL=claude-haiku-4-5-20251001
FULL_MODEL=claude-sonnet-4-20250514

# Google Gemini
GEMINI_API_KEY=AI...
MINI_MODEL=gemini/gemini-2.0-flash
FULL_MODEL=gemini/gemini-2.5-pro-preview-05-06
MONTHLY_TOKEN_BUDGET=5.0   # Gemini free tier: 15 RPM — see Known Quirks
```

---

### Recommended First Run Order

1. Start Ollama server: `ollama serve`
2. **Onboarding** (sidebar) → upload CV → fill 5-step form → Save Profile
3. **Job Search** → click "Search Jobs" → click "Score Unscored Jobs"
4. **Dashboard** → review pipeline stats
5. **CV Manager** → select a job → Score → optionally Rewrite

---

## Active Configuration

This is what is currently set in `.env` for this project:

| Variable | Value | Notes |
|---|---|---|
| `GEMINI_API_KEY` | set | Present but **not used** — models are set to Ollama |
| `OPENAI_API_KEY` | empty | Not used |
| `ANTHROPIC_API_KEY` | empty | Not used |
| `MINI_MODEL` | `ollama/llama3.2` | All scoring, summarization, onboarding |
| `FULL_MODEL` | `ollama/llama3.2` | CV rewriting (same model, runs locally) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Default Ollama server address |
| `MONTHLY_TOKEN_BUDGET` | `0` | Unlimited (Ollama is free, no token cost) |
| `JOBSPY_RESULTS_PER_SITE` | `10` | JobSpy fetches 10 jobs per site (LinkedIn + Indeed + Glassdoor = 30 max per search) |
| `DATABASE_URL` | `sqlite:///data/app.db` | Local SQLite database |
| `SERPAPI_API_KEY` | empty | SerpAPI not configured — using JobSpy instead |
| `ADZUNA_APP_ID/KEY` | empty | Adzuna not configured |

> **Cost:** $0.00/month. Everything runs locally via Ollama.

---

## Configuration Reference

All configuration is read from environment variables via `.env`. The `config.py` module loads them into a `Settings` singleton (`settings` object) that is imported across the codebase.

```python
# config.py — Settings class fields (all read from .env)

# LLM Provider Keys (set at least one, OR use Ollama for free local models)
OPENAI_API_KEY      # OpenAI API key
ANTHROPIC_API_KEY   # Anthropic API key
GEMINI_API_KEY      # Google Gemini API key

# Job Search Source Keys (all optional — JobSpy + Remotive work without keys)
SERPAPI_API_KEY     # SerpAPI (Google Jobs) key — optional
ADZUNA_APP_ID       # Adzuna application ID — optional
ADZUNA_APP_KEY      # Adzuna application key — optional

# Model Selection
MINI_MODEL          # Default: "gpt-4o-mini" — used for scoring, summarization, onboarding
FULL_MODEL          # Default: "gpt-4o" — used ONLY for CV rewriting
OLLAMA_BASE_URL     # Default: "http://localhost:11434" — Ollama server address

# JobSpy Scraper Config
JOBSPY_RESULTS_PER_SITE  # Default: 15 — results per platform (LinkedIn/Indeed/Glassdoor)
                          # Set to 10 for faster searches, 25 for broader coverage
                          # Total results = JOBSPY_RESULTS_PER_SITE × 3 platforms

# Budget & Storage
MONTHLY_TOKEN_BUDGET  # Default: 10.0 (USD). Set 0 for unlimited (use 0 for Ollama).
DATABASE_URL          # Default: "sqlite:///data/app.db"
UPLOAD_DIR            # Auto-resolved: <project_root>/data/uploads/ (not in .env)
DB_PATH               # Auto-resolved: <project_root>/data/app.db (not in .env)
```

### Model String Examples

| Provider | MINI_MODEL | FULL_MODEL | Cost |
|----------|-----------|-----------|------|
| **Ollama** ⭐ | `ollama/llama3.2` | `ollama/llama3.1` | **Free** |
| Ollama (low RAM) | `ollama/phi3:mini` | `ollama/gemma2:2b` | **Free** |
| OpenAI | `gpt-4o-mini` | `gpt-4o` | ~$0.62/month |
| Anthropic | `claude-haiku-4-5-20251001` | `claude-sonnet-4-20250514` | ~$0.65/month |
| Google Gemini | `gemini/gemini-2.0-flash` | `gemini/gemini-2.5-pro-preview-05-06` | Free tier available |

> **Note:** litellm is the unified LLM gateway. Any model string supported by litellm will work — see https://docs.litellm.ai/docs/providers

> **Ollama JSON mode:** Ollama does not support `response_format={"type":"json_object"}`. `llm_client.py` detects `ollama/` prefix and appends a JSON instruction to the prompt instead. This is handled automatically — no config needed.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     Streamlit UI (pages/)                 │
│  Dashboard | Onboarding | Job Search | My Jobs | CV Mgr  │
└───────────────────────┬──────────────────────────────────┘
                        │ user actions trigger
                        ▼
┌──────────────────────────────────────────────────────────┐
│               agents/ (Scoped LLM handlers)              │
│  orchestrator.py (NO LLM) | onboarding | job_search     │
│  cv_scorer | cv_rewriter                                 │
└───────────┬──────────────────────┬───────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────┐   ┌──────────────────────────────────┐
│   services/       │   │   services/job_sources/           │
│  llm_client.py    │   │  jobspy | remotive | serpapi      │
│  cache.py         │   │  adzuna | scraper                 │
│  cv_parser.py     │   └──────────────────────────────────┘
└───────┬───────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│               SQLite Database (data/app.db)               │
│  user_profiles | jobs | llm_cache | token_usage          │
└──────────────────────────────────────────────────────────┘
```

### Request Lifecycle (example: Score CV)

```
User clicks "Score My CV" in UI
  → pages/5_CV_Manager.py calls agents/cv_scorer.score_single_job(db, profile, job)
    → cv_scorer checks keyword overlap (rule-based, zero tokens)
      → if overlap < 20%: returns rule-based low score (no LLM call)
      → else: calls services/llm_client.llm_call(...)
        → llm_client checks services/cache.get_cached_response(db, model, prompt)
          → cache HIT: returns stored text, logs zero tokens
          → cache MISS: checks monthly budget → calls litellm.completion(...)
            → stores response in llm_cache table
            → logs token usage in token_usage table
            → returns response text
    → cv_scorer parses JSON response, writes score to jobs table
  → UI displays score, matches, gaps
```

---

## Complete File Reference

### Entry Point

#### `app.py`
- Streamlit entry point. Calls `init_db()` to create all tables on first run.
- Sets page config: wide layout, expanded sidebar, page title = "Job Search Agent".
- Renders a static welcome/instructions page at the root URL (`/`).
- **Does not contain any business logic.** All logic lives in `pages/`, `agents/`, and `services/`.

---

### Config

#### `config.py`
- Loads `.env` via `python-dotenv`.
- Defines `class Settings` with all config fields as class attributes.
- Exports a singleton: `settings = Settings()`. **Import `settings` from this module everywhere.**
- Key paths auto-resolved:
  - `UPLOAD_DIR = <project_root>/data/uploads/`
  - `DB_PATH = <project_root>/data/app.db`

---

### Database Layer

#### `database.py`
- Creates `data/` directory if it doesn't exist.
- Creates SQLAlchemy `engine` using `sqlite:///` + `settings.DB_PATH`.
- `SessionLocal = sessionmaker(bind=engine)` — use this to get DB sessions in pages.
- `Base` — `DeclarativeBase` subclass. All ORM models inherit from this.
- `get_db()` — generator that yields a session and closes it after use (used in non-Streamlit contexts).
- `init_db()` — imports all models (to register them with `Base.metadata`) then calls `Base.metadata.create_all()`. Called at app startup in every page file.

**Pattern used in every page:**
```python
db = SessionLocal()
try:
    # ... business logic using db ...
finally:
    db.close()
```

---

### ORM Models

All models are in `models/` and inherit from `database.Base`.

#### `models/user.py` — `UserProfile`
Table: `user_profiles`

| Column              | Type        | Notes                                              |
|---------------------|-------------|----------------------------------------------------|
| `id`                | Integer PK  | Auto-increment                                     |
| `name`              | String(200) |                                                    |
| `email`             | String(200) |                                                    |
| `phone`             | String(50)  |                                                    |
| `location`          | String(200) | User's current city                                |
| `preferred_roles`   | JSON        | List of strings e.g. `["Software Engineer"]`       |
| `preferred_locations` | JSON      | List of strings e.g. `["Remote", "New York"]`      |
| `remote_preference` | String(50)  | One of: `remote / hybrid / onsite / any`           |
| `min_salary`        | Float       | Nullable. Annual salary in USD.                    |
| `experience_summary`| Text        | 2-3 sentence summary extracted by LLM              |
| `projects_summary`  | Text        | User-entered free-text about their key projects     |
| `skills`            | JSON        | List of strings — merged from LLM + keyword match  |
| `raw_cv_path`       | String(500) | Absolute path to uploaded original CV file          |
| `parsed_cv_text`    | Text        | Full text extracted from CV (rule-based, no LLM)   |
| `structured_cv`     | JSON        | Full structured profile extracted by LLM (see below)|
| `created_at`        | DateTime    | UTC                                                |
| `updated_at`        | DateTime    | UTC, auto-updated on change                        |

**`structured_cv` JSON shape** (from `extract_profile.txt` prompt):
```json
{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "most_recent_role": "",
  "years_experience": 0,
  "education_level": "",
  "skills": ["skill1", "skill2"],
  "experience_summary": "2-3 sentences",
  "suggested_roles": ["role1", "role2"]
}
```

> **Important:** Only one `UserProfile` row is ever created per database. The app always uses `.first()` to fetch it.

---

#### `models/job.py` — `Job`
Table: `jobs`

| Column               | Type         | Notes                                                         |
|----------------------|--------------|---------------------------------------------------------------|
| `id`                 | Integer PK   | Auto-increment                                                |
| `external_id`        | String(200)  | Source-specific job ID (used for dedup)                       |
| `source`             | String(50)   | One of: `jobspy-linkedin / jobspy-indeed / serpapi / adzuna / remotive / scraper` |
| `title`              | String(500)  |                                                               |
| `company`            | String(300)  |                                                               |
| `location`           | String(300)  |                                                               |
| `remote_type`        | String(50)   | One of: `remote / hybrid / onsite / unknown`                  |
| `salary_min`         | Float        | Nullable                                                      |
| `salary_max`         | Float        | Nullable                                                      |
| `description_raw`    | Text         | HTML-stripped raw job description                             |
| `description_summary`| Text         | 3-bullet LLM summary (~100 words)                             |
| `requirements`       | Text         | JSON string — list of requirement strings e.g. `["Python", "AWS"]` |
| `url`                | String(1000) | Link to original job posting                                  |
| `posted_date`        | String(100)  | Raw string from source API                                    |
| `discovered_at`      | DateTime     | UTC timestamp when job was first found                        |
| `status`             | String(50)   | Pipeline status — see below                                   |
| `cv_score`           | Float        | Nullable. 0–100 match score.                                  |
| `score_explanation`  | Text         | 1-sentence LLM explanation of score                           |
| `score_details`      | Text         | JSON string — `{"score":X,"matches":[],"gaps":[],"explanation":""}` |
| `rewritten_cv_path`  | String(500)  | Absolute path to rewritten CV `.md` file                      |
| `created_at`         | DateTime     | UTC                                                           |
| `updated_at`         | DateTime     | UTC, auto-updated on change                                   |

**Job status pipeline:**
```
new → saved → applied → interviewing → rejected
           ↘ dismissed (at any point)
```

**`requirements` field quirk:** Stored as a JSON *string* (not a native JSON column) because some early data may not be valid JSON. Always parse with:
```python
json.loads(job.requirements or "[]")
```
The `_parse_reqs()` helper in `cv_scorer.py` handles this safely.

---

#### `models/cache.py` — `LLMCache` + `TokenUsage`

**`LLMCache`** — Table: `llm_cache`

| Column         | Type        | Notes                                              |
|----------------|-------------|----------------------------------------------------|
| `id`           | Integer PK  |                                                    |
| `prompt_hash`  | String(64)  | SHA256 hex of `"model:full_prompt"`. Unique + indexed. |
| `model`        | String(100) | Model string used for this call                    |
| `response_text`| Text        | Cached LLM response                                |
| `tokens_input` | Integer     | Input token count                                  |
| `tokens_output`| Integer     | Output token count                                 |
| `created_at`   | DateTime    | UTC — used to check TTL expiry                     |
| `ttl_hours`    | Integer     | Default 720 (30 days). 8760 = 1 year.              |

**`TokenUsage`** — Table: `token_usage`

| Column        | Type        | Notes                                              |
|---------------|-------------|----------------------------------------------------|
| `id`          | Integer PK  |                                                    |
| `task_type`   | String(50)  | One of: `score / rewrite / search / onboard / summarize` |
| `model`       | String(100) | Model string                                       |
| `tokens_input`| Integer     |                                                    |
| `tokens_output`| Integer    |                                                    |
| `cost_usd`    | Float       | Estimated USD cost based on `COST_MAP` in `llm_client.py` |
| `timestamp`   | DateTime    | UTC — used for monthly budget calculation          |

---

### Agents

All agents in `agents/` are thin wrappers around specific LLM tasks. Each agent is responsible for exactly one operation. **No agent ever starts another LLM call chain unprompted.**

#### `agents/orchestrator.py`
**Zero LLM calls. Pure Python dispatch.**

Exports these functions, all used directly by page files:

| Function | Signature | Returns |
|---|---|---|
| `get_profile` | `(db) → UserProfile \| None` | First (and only) user profile row |
| `has_profile` | `(db) → bool` | True if any profile row exists |
| `has_cv` | `(db) → bool` | True if profile exists and `parsed_cv_text` is non-empty |
| `get_jobs` | `(db, status?, min_score?) → list[Job]` | Jobs ordered by `cv_score DESC NULLS FIRST` |
| `get_job` | `(db, job_id) → Job \| None` | Single job by primary key |
| `update_job_status` | `(db, job_id, status) → Job \| None` | Updates status, commits, refreshes |
| `get_dashboard_stats` | `(db) → dict` | Aggregated stats dict (see below) |

**`get_dashboard_stats` return shape:**
```python
{
    "total_jobs": int,
    "new_jobs": int,
    "saved_jobs": int,
    "applied_jobs": int,
    "interviewing": int,
    "monthly_cost": float,      # sum of token_usage.cost_usd for current calendar month
    "monthly_tokens": int,      # sum of token_usage.tokens_in + tokens_out for current month
    "cost_by_task": dict,       # { "score": 0.002, "rewrite": 0.06, ... }
}
```

---

#### `agents/onboarding.py`

**Functions:**

`save_cv_file(file_bytes: bytes, filename: str) → str`
- Saves uploaded CV bytes to `settings.UPLOAD_DIR/<filename>`
- Returns absolute file path

`process_cv(db: Session, file_path: str) → dict`
- Calls `services/cv_parser.extract_text()` (rule-based, zero tokens)
- Calls `services/cv_parser.extract_sections()` (rule-based)
- Calls `services/cv_parser.extract_skills_keywords()` (keyword matching, zero tokens)
- Makes **one mini-model LLM call** using `prompts/extract_profile.txt` to get structured JSON
- Truncates CV to 3000 chars before sending to LLM to save tokens
- Merges LLM-extracted skills with keyword-extracted skills (deduped)
- Cache TTL: 8760 hours (1 year) — CV structuring is unlikely to differ on reruns
- Returns: `{ "parsed_cv_text": str, "sections": dict, "structured_cv": dict, "skills": list }`

`save_profile(db, name, email, phone, ...) → UserProfile`
- Upsert pattern: fetches existing profile or creates new one
- Only overwrites fields if the new value is non-empty (preserves existing data)
- Writes `structured_cv`, `parsed_cv_text`, `skills`, `experience_summary` from `cv_data` if provided

---

#### `agents/job_search.py`

**Functions:**

`search_jobs(db, profile, custom_query="", custom_location="") → list[Job]`
- Builds search queries from `profile.preferred_roles × profile.preferred_locations` if no custom query
- For each query: calls `_fetch_from_all_sources()` (all 5 sources in parallel via `asyncio.gather`)
- For each raw result: checks `_is_duplicate()` (rapidfuzz, zero tokens), strips HTML, calls `_summarize_job()`
- **⚠️ 4-second sleep between each job's summarization call** (`time.sleep(4)`) — intentional to stay under Gemini free-tier 15 RPM limit. This makes search slow but avoids rate limit errors.
- Saves new `Job` rows to DB, commits in bulk at the end

`_is_duplicate(new_job, existing_jobs) → bool`
- Returns True if title similarity > 85% AND company similarity > 80% (using `fuzz.ratio`)
- OR if `external_id` matches exactly
- Zero LLM tokens

`_summarize_job(db, description) → dict`
- Skips LLM if description < 50 chars
- Truncates description to 2000 chars
- Returns: `{ "summary": "• bullet\n• bullet\n• bullet", "requirements": ["req1", "req2"] }`
- Cache TTL: 168 hours (7 days)

`_strip_html(text) → str`
- Regex-based HTML tag removal + whitespace normalization

`_build_queries(profile) → list[dict]`
- Returns `[{"query": role, "location": loc}, ...]` for each role/location combination
- Falls back to `["software engineer"]` / `[""]` if profile has no preferences

---

#### `agents/cv_scorer.py`

**Functions:**

`score_single_job(db, profile, job) → dict`
- Pre-filter: computes `_keyword_overlap(profile.skills, job_requirements)`
  - If overlap < 20% AND requirements are non-empty → skips LLM, assigns `score = int(overlap * 100)`, returns immediately
- Otherwise: calls mini model with `prompts/score_cv.txt`
- Prompt structure:
  ```
  JOB REQUIREMENTS: [list]
  JOB TITLE: <title>
  CANDIDATE SKILLS: [list]
  CANDIDATE EXPERIENCE: <experience_summary>
  ```
- Returns: `{ "score": 0-100, "matches": [str], "gaps": [str], "explanation": str }`
- Writes score back to `job.cv_score`, `job.score_explanation`, `job.score_details` and commits

`score_batch(db, profile, jobs) → list[dict]`
- Processes jobs in batches of 5
- Within each batch: pre-filters low-overlap jobs, then sends remaining as a single LLM call
- Batch prompt: all jobs in one message asking for a JSON array of scores
- Handles both `{"scores": [...]}` and bare `[...]` response shapes
- Falls back to score=50 if JSON parsing fails

`_keyword_overlap(skills, requirements) → float`
- Returns 0.5 (neutral) if requirements list is empty
- Otherwise: `len(skills ∩ requirements) / len(requirements)` (case-insensitive set intersection)

`_parse_reqs(job) → list[str]`
- Handles both native list and JSON-string formats of `job.requirements`

---

#### `agents/cv_rewriter.py`

**Functions:**

`rewrite_cv_for_job(db, profile, job) → str`
- Uses `settings.FULL_MODEL` (expensive — only call on explicit user action)
- `json_mode=False` — expects Markdown, not JSON
- Cache TTL: 720 hours (30 days)
- Prompt structure:
  ```
  TARGET JOB:
  Title: <title>
  Company: <company>
  Key Requirements: <requirements JSON>

  CURRENT CV:
  <parsed_cv_text[:4000]>
  ```
- Saves output to `data/uploads/rewritten_cv_<job_id>.md`
- Writes `job.rewritten_cv_path` and commits
- Returns the rewritten CV markdown string

---

### Services

#### `services/llm_client.py`

The **central gateway for all LLM calls**. Every agent routes through here.

**`llm_call(db, prompt, task_type, system, model, use_cache, cache_ttl, json_mode) → str`**

Full parameter reference:
| Param | Default | Notes |
|---|---|---|
| `db` | required | SQLAlchemy session |
| `prompt` | required | User message content |
| `task_type` | `"general"` | Used for budget tracking. One of: `score/rewrite/search/onboard/summarize` |
| `system` | `""` | System prompt. Kept short (40-60 tokens) to minimize costs. |
| `model` | `settings.MINI_MODEL` | Override to use FULL_MODEL for rewrites |
| `use_cache` | `True` | Set False to force fresh call |
| `cache_ttl` | `720` | Cache TTL in hours |
| `json_mode` | `True` | Adds `response_format={"type":"json_object"}` for cloud models. For Ollama, appends "Respond with valid JSON only." to prompt instead. |

**Internal flow:**
1. Build `full_prompt = system + "\n" + prompt` for cache key
2. Check `services/cache.get_cached_response(db, model, full_prompt)` → return if hit
3. Check monthly budget via `_check_budget(db)` → return error JSON if exceeded
4. Build messages array: `[{role:system}, {role:user}]`
5. Call `litellm.completion(**kwargs)` with exponential backoff (4 attempts: 5s, 10s, 20s, 40s) on `RateLimitError`
6. Extract `response.choices[0].message.content`
7. Log to `token_usage` table via `_log_usage()`
8. Store in cache via `services/cache.set_cached_response()`
9. Return text

**Cost estimation (`COST_MAP`):**
```python
COST_MAP = {
    "gpt-4o-mini": (0.15, 0.60),         # (input $/1M, output $/1M)
    "gpt-4o": (2.50, 10.00),
    "claude-haiku": (0.25, 1.25),
    "claude-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
}
```
Unknown models fall back to: `(tokens_in * 1.0 + tokens_out * 3.0) / 1_000_000`

---

#### `services/cache.py`

Thin wrapper over the `LLMCache` ORM model.

`make_cache_key(model, prompt) → str`
- `SHA256(f"{model}:{prompt}")` — cache key is model-specific

`get_cached_response(db, model, prompt) → str | None`
- Returns `None` if: (a) no row found, or (b) `created_at + ttl_hours < now`
- Expired entries are **deleted from DB** on access

`set_cached_response(db, model, prompt, response, tokens_in, tokens_out, ttl_hours=720)`
- Upserts: updates existing row if hash matches, otherwise inserts new

---

#### `services/cv_parser.py`

All functions are **zero LLM tokens** — pure Python parsing.

`extract_text(file_path) → str`
- Routes to the appropriate extractor based on file extension
- Supported: `.pdf` (PyMuPDF/fitz), `.docx`/`.doc` (python-docx), `.txt` (plain read)
- Raises `ValueError` for unsupported types

`extract_sections(text) → dict[str, str]`
- Regex-based section detection. Looks for headers matching:
  - `summary/profile/objective/about` → `"summary"`
  - `experience/work history/employment` → `"experience"`
  - `education/academics/qualifications` → `"education"`
  - `skills/technical/technologies` → `"skills"`
  - `projects/portfolio` → `"projects"`
  - `certif/licens/credentials` → `"certifications"`
- Lines before any section header go into `"header"` section
- Only matches if the line is < 60 chars (avoids false positives in body text)

`extract_skills_keywords(text) → list[str]`
- Scans text for ~50 hardcoded skills (Python, JavaScript, AWS, Docker, etc.)
- Case-insensitive substring match
- **To add new skills:** append to the `known_skills` list in this function

---

### Job Sources

All sources implement `JobSource` base class from `services/job_sources/base.py`.

**`JobResult` dataclass fields:**
```python
@dataclass
class JobResult:
    external_id: str = ""
    source: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    remote_type: str = "unknown"   # remote / hybrid / onsite / unknown
    salary_min: float | None = None
    salary_max: float | None = None
    description: str = ""
    url: str = ""
    posted_date: str = ""
    requirements: list[str] = field(default_factory=list)
```

**`JobSource` interface:**
```python
class JobSource:
    name: str = "base"

    async def search(self, query: str, location: str = "", **kwargs) -> list[JobResult]:
        raise NotImplementedError
```

All sources are called together via `asyncio.gather()` in `_fetch_from_all_sources()`.

---

#### `services/job_sources/jobspy_source.py` — `JobSpySource`
- Uses `python-jobspy` to scrape **LinkedIn, Indeed, Glassdoor** without API keys
- Returns up to 15 results (configurable via `num` kwarg)
- Only fetches jobs posted within the last 72 hours (`hours_old=72`)
- `country_indeed` auto-set to `"india"` if `"india"` in location string, otherwise `"usa"`
- Gracefully returns `[]` if `jobspy` or `pandas` are not installed
- Source name in DB: `jobspy-linkedin`, `jobspy-indeed`, `jobspy-glassdoor`

#### `services/job_sources/remotive_source.py` — `RemotiveSource`
- Free REST API at `https://remotive.com/api/remote-jobs`
- No API key required
- Returns remote-only jobs worldwide
- Maps `tags` array from API as `requirements`
- Always sets `remote_type = "remote"`

#### `services/job_sources/serpapi_source.py` — `SerpAPISource`
- Google Jobs results via SerpAPI (`engine=google_jobs`)
- **Skips entirely if `settings.SERPAPI_API_KEY` is empty**
- Endpoint: `https://serpapi.com/search`
- Infers `remote_type` from location string: "remote" in location → `remote`, else `unknown`
- Extracts salary from `detected_extensions` dict

#### `services/job_sources/adzuna_source.py` — `AdzunaSource`
- Adzuna REST API
- **Skips entirely if `ADZUNA_APP_ID` or `ADZUNA_APP_KEY` are empty**
- Returns up to 20 results

#### `services/job_sources/scraper.py` — `WebScraperSource`
- Google search scraping fallback using `httpx` + `beautifulsoup4`
- Fragile — depends on Google search result HTML structure
- Used as last resort when other sources fail or are unconfigured

---

### Prompt Templates

All prompts are in `prompts/` — minimal by design to save tokens. Each is a system prompt loaded as a string.

#### `prompts/extract_profile.txt` (~40 tokens)
```
Extract structured profile from this CV. Return JSON only, no explanation.
{"name":"","email":"","phone":"","location":"","most_recent_role":"","years_experience":0,"education_level":"","skills":["skill1"],"experience_summary":"2-3 sentences","suggested_roles":["role1","role2"]}
```
Used by: `agents/onboarding.process_cv()`

#### `prompts/summarize_job.txt` (~40 tokens)
```
Summarize this job posting in 3 bullet points, max 100 words total. Extract key requirements as a list. Return JSON:
{"summary":"• point1\n• point2\n• point3","requirements":["req1","req2"]}
```
Used by: `agents/job_search._summarize_job()`

#### `prompts/score_cv.txt` (~30 tokens)
```
Score candidate fit for this job 0-100. Return JSON only.
{"score":0,"matches":["matching skill/experience"],"gaps":["missing requirement"],"explanation":"1 sentence"}
```
Used by: `agents/cv_scorer.score_single_job()` and `score_batch()`

#### `prompts/rewrite_cv.txt` (~60 tokens)
```
Rewrite this CV to maximize relevance for the target job. Rules:
- Reorder and emphasize relevant experience
- Mirror keywords from job requirements
- Keep same length as original
- Do not fabricate experience
- Output in clean markdown format
```
Used by: `agents/cv_rewriter.rewrite_cv_for_job()`

---

### Pages (Streamlit UI)

Every page follows the same pattern:
1. `init_db()` — ensures tables exist (idempotent)
2. `db = SessionLocal()` — open session
3. Business logic wrapped in `try/finally: db.close()`
4. Guard clauses using `has_profile(db)` / `has_cv(db)` to redirect incomplete users

#### `pages/1_Dashboard.py`
- Shows 5 metric cards: Total Jobs, New, Saved, Applied, Interviewing
- Bar chart: monthly cost by task type (Plotly)
- Pie chart: jobs by status (Plotly)
- List: top 10 jobs with cv_score ≥ 50, with color coding (≥70: green, ≥50: orange, <50: red)
- Redirects to Onboarding if no profile exists

#### `pages/2_Onboarding.py`
- Shows current profile summary if one exists (allows updating)
- Step 1: File uploader → calls `process_cv()` (1 mini model call)
- Prefill logic: saved value → LLM-extracted value → empty (in that priority)
- Steps 2-5 all wrapped in a single `st.form` to avoid "Press Enter" gotchas
- Step 5: project description textarea
- On submit: calls `save_profile()` then links to Job Search

#### `pages/3_Job_Search.py`
- Search form: custom query + location (or leave blank to use profile preferences)
- "Score Unscored Jobs" button (disabled if no CV or no unscored jobs)
- Filter controls: status dropdown, minimum score slider, sort order
- Job cards in expanders: shows company, location, salary, source, summary, score analysis, matches/gaps, URL
- Action buttons: Save / Mark Applied / Dismiss — each calls `update_job_status()` and reruns

#### `pages/4_My_Jobs.py`
- Tabbed view: Saved | Applied | Interviewing | Rejected
- Each job card shows location, salary, summary, score explanation, posting URL
- "Move to:" column with one button per valid target status
- Pipeline summary metric cards at the bottom

#### `pages/5_CV_Manager.py`
- CV overview: name, skills count, experience snippet, character count
- "View Full CV Text" expander
- Job selector dropdown (all jobs in DB)
- "Score My CV" button → calls `score_single_job()` → shows score, explanation, matches, gaps
- "Rewrite CV for This Job" button → calls `rewrite_cv_for_job()` (uses FULL model)
- Shows existing rewritten CV as rendered Markdown + download button
- "All Tailored CVs" section with download buttons for all past rewrites

---

## JobSpy — Primary Job Source

JobSpy (`python-jobspy`) is the **primary and default job discovery source** in this project. It scrapes **LinkedIn, Indeed, and Glassdoor simultaneously without any API keys**.

### Why JobSpy is #1 in source order
In `agents/job_search._fetch_from_all_sources()`, the sources list is:
```python
sources = [JobSpySource(), RemotiveSource(), SerpAPISource(), AdzunaSource(), WebScraperSource()]
```
JobSpy is first because it gives the most results without any account setup. With `JOBSPY_RESULTS_PER_SITE=10`, one search yields up to 30 jobs (10 × 3 platforms) from real job boards.

### How JobSpy Works
- Uses `python-jobspy` (wraps `scrape_jobs()` from the `jobspy` library)
- Scrapes the actual job board HTML/APIs client-side — no middleman API
- Filters to jobs posted within the **last 72 hours** (`hours_old=72`)
- Detects India-based searches and sets `country_indeed="india"` automatically
- Results are returned as a pandas DataFrame, then converted to `JobResult` objects

### JobSpy Config
| Setting | .env Key | config.py Field | Default |
|---|---|---|---|
| Results per site | `JOBSPY_RESULTS_PER_SITE` | `settings.JOBSPY_RESULTS_PER_SITE` | `15` |
| Max total results | (derived) | `JOBSPY_RESULTS_PER_SITE × 3` | `45` |
| Recency filter | (hardcoded) | `hours_old=72` | 3 days |

> **Note:** After wiring `JOBSPY_RESULTS_PER_SITE` into `config.py`, the value from `.env` is now respected. Previously the hardcoded default was 15.

### JobSpy Limitations
- Depends on scraping — LinkedIn/Indeed HTML changes can break it temporarily
- LinkedIn sometimes rate-limits scraping; if you see empty results, wait a few minutes
- `pandas` must be installed (included in `requirements.txt` via `python-jobspy`)
- Cannot filter by exact salary range (salary data may be empty for many listings)

---

## Data Flow Walkthroughs

### Flow 1: First-Time Onboarding

```
User uploads CV PDF
  → save_cv_file() writes to data/uploads/
  → extract_text() reads PDF via PyMuPDF → raw text
  → extract_sections() → dict of {section_name: text}
  → extract_skills_keywords() → list of detected skills (keyword match)
  → llm_call(mini_model, extract_profile.txt + first 3000 chars of CV text)
      → Cache MISS: calls LLM, stores in llm_cache
      → Returns structured_cv JSON
  → Merges LLM skills + keyword skills → deduplicated list
  → Form submitted → save_profile() upserts UserProfile row
```

### Flow 2: Job Search

```
User clicks "Search Jobs" (empty query → uses profile preferences)
  → _build_queries(profile) → [{"query": role, "location": loc}, ...]
  → For each query:
      asyncio.gather([JobSpy, Remotive, SerpAPI, Adzuna, Scraper])
      → All 5 sources run in parallel
      → Collect all JobResult objects
  → For each JobResult:
      _is_duplicate() (rapidfuzz fuzzy match) → skip if duplicate
      _strip_html() → clean description text
      time.sleep(4) → rate limit buffer for Gemini free tier
      _summarize_job() → llm_call(mini_model, summarize_job.txt + desc[:2000])
          → Cache check → LLM call or cache hit
          → Returns {summary, requirements}
      Creates Job row, adds to DB
  → db.commit() → all new jobs persisted
```

### Flow 3: Batch Scoring

```
User clicks "Score Unscored Jobs"
  → Gets all jobs where cv_score IS NULL and status = "new"
  → score_batch(db, profile, unscored_jobs)
  → Processes in batches of 5:
      For each job in batch:
          _keyword_overlap(profile.skills, job_requirements) < 20%?
              YES → rule-based score, no LLM, append result
              NO  → add to llm_batch
      If llm_batch is empty → skip to next batch
      If llm_batch has 1 job → score_single_job()
      If llm_batch has 2-5 jobs → single batch LLM call
          → llm_call(mini_model, score_cv.txt + all jobs text)
          → Parse JSON array of scores
          → Write each score back to job row
  → db.commit()
```

### Flow 4: CV Rewrite

```
User selects job in CV Manager → clicks "Rewrite CV for This Job"
  → rewrite_cv_for_job(db, profile, job)
  → llm_call(
        model=settings.FULL_MODEL,  ← expensive model
        system=rewrite_cv.txt,
        prompt="TARGET JOB:\n<title/company/requirements>\n\nCURRENT CV:\n<cv_text[:4000]>",
        json_mode=False,            ← wants markdown, not JSON
        cache_ttl=720               ← 30 day cache
    )
  → Saves response to data/uploads/rewritten_cv_<job_id>.md
  → Updates job.rewritten_cv_path in DB
  → Returns markdown string
  → UI renders markdown + shows download button
```

---

## Database Schema

```sql
-- Auto-created by SQLAlchemy on init_db()

CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200), email VARCHAR(200), phone VARCHAR(50),
    location VARCHAR(200), preferred_roles JSON, preferred_locations JSON,
    remote_preference VARCHAR(50) DEFAULT 'any',
    min_salary FLOAT, experience_summary TEXT, projects_summary TEXT,
    skills JSON, raw_cv_path VARCHAR(500), parsed_cv_text TEXT,
    structured_cv JSON, created_at DATETIME, updated_at DATETIME
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id VARCHAR(200), source VARCHAR(50),
    title VARCHAR(500), company VARCHAR(300),
    location VARCHAR(300), remote_type VARCHAR(50),
    salary_min FLOAT, salary_max FLOAT,
    description_raw TEXT, description_summary TEXT,
    requirements TEXT,  -- JSON string, NOT native JSON column
    url VARCHAR(1000), posted_date VARCHAR(100),
    discovered_at DATETIME, status VARCHAR(50) DEFAULT 'new',
    cv_score FLOAT, score_explanation TEXT,
    score_details TEXT,  -- JSON string
    rewritten_cv_path VARCHAR(500),
    created_at DATETIME, updated_at DATETIME
);

CREATE TABLE llm_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash VARCHAR(64) UNIQUE,  -- SHA256, indexed
    model VARCHAR(100), response_text TEXT,
    tokens_input INTEGER, tokens_output INTEGER,
    created_at DATETIME, ttl_hours INTEGER DEFAULT 720
);

CREATE TABLE token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type VARCHAR(50), model VARCHAR(100),
    tokens_input INTEGER, tokens_output INTEGER,
    cost_usd FLOAT, timestamp DATETIME
);
```

> **Reset DB:** Delete `data/app.db` and restart. Tables are auto-recreated. All jobs, profiles, and cache are lost.

---

## LLM Strategy & Token Optimization

### Per-Operation Cost Breakdown

| Operation | Model | ~Tokens/Call | ~Cost/Call | Frequency |
|-----------|-------|-------------|-----------|-----------|
| CV profile extraction | Mini | ~500 | $0.0001 | Once at onboarding |
| Job summarization | Mini | ~400 | $0.0001 | Per new job found |
| CV scoring (single) | Mini | ~650 | $0.0001 | Per scored job |
| CV scoring (batch of 5) | Mini | ~1800 | $0.0003 | Per 5 jobs |
| CV rewriting | Full | ~3500 | $0.03 | On-demand only |

### Strategies (Ranked by Impact)

| # | Strategy | Implementation |
|---|-----------|----------------|
| 1 | **No agent loop** | Orchestrator is pure Python — no "decide what to do next" LLM calls |
| 2 | **Model tiering** | Mini model for 95% of calls; full model only for rewrites |
| 3 | **SHA256 semantic caching** | 100% hit rate on identical requests — zero tokens |
| 4 | **Rule-based parsing** | CV extraction, dedup, skill detection, filtering — all zero tokens |
| 5 | **Keyword pre-filtering** | <20% overlap → no LLM call (saves 30-50% of scoring calls) |
| 6 | **Batch scoring** | 5 jobs per call, amortizes system prompt + CV context (~40% savings) |
| 7 | **Prompt compression** | Prompts are 30-60 tokens max; CV/descriptions truncated before sending |
| 8 | **Monthly budget cap** | Hard stop in `_check_budget()` before every LLM call |

### Estimated Monthly Cost

For a typical search (100 jobs found, 20 rewrites):

| Task | Calls | Est. Cost |
|------|-------|-----------|
| Job summaries | 100 | $0.01 |
| CV scoring (20 batches of 5) | 20 | $0.006 |
| CV rewrites | 20 | $0.60 |
| Profile extraction | 1 | $0.0001 |
| **Total** | | **~$0.62/month** |

---

## Job Sources Reference

| Source | Class | Active? | Key Required | ~Results/search | Notes |
|--------|-------|---------|-------------|-----------------|-------|
| **JobSpy** | `JobSpySource` | ✅ **Primary** | ❌ None | `JOBSPY_RESULTS_PER_SITE × 3` | Scrapes LinkedIn, Indeed, Glassdoor |
| Remotive | `RemotiveSource` | ✅ Active | ❌ None | 20 | Remote-only jobs worldwide |
| SerpAPI | `SerpAPISource` | ⚠️ Disabled | ✅ `SERPAPI_API_KEY` | 20 | Not set in current .env |
| Adzuna | `AdzunaSource` | ⚠️ Disabled | ✅ `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | 20 | Not set in current .env |
| WebScraper | `WebScraperSource` | ✅ Fallback | ❌ None | Varies | Google scraping, fragile |

All sources are queried **in parallel** via `asyncio.gather()`. Results are merged and fuzzy-deduplicated before storage.

---

## Known Quirks & Gotchas

### 1. The 4-Second Sleep in `job_search.py`
`time.sleep(4)` is called **between each job's summarization** (`agents/job_search.py` line ~119). This was originally added to stay under Gemini free tier's 15 RPM limit.
- **With Ollama** (current setup): Ollama has no rate limit, so this sleep is unnecessary but harmless. You can safely remove it for faster searches.
- **With Gemini free tier**: Keep this sleep. For 50+ jobs, total search time will be several minutes.
- To disable: comment out `time.sleep(4)` in `agents/job_search.py`

### 2. `requirements` Column is a JSON String, Not JSON
Despite looking like a list in code, `jobs.requirements` is stored as a raw JSON **string** (TEXT column). Always parse with:
```python
json.loads(job.requirements or "[]")
```
The `_parse_reqs()` helper in `cv_scorer.py` handles both list and string formats safely. Don't bypass it.

### 3. Only One UserProfile Row Ever Exists
The app always queries `.first()` for the profile. There's no multi-user support. If you need to switch profiles, delete `data/app.db` and re-run onboarding.

### 4. JobSpy is the Primary Job Source (not just a fallback)
`services/job_sources/jobspy_source.py` is listed **first** in `_fetch_from_all_sources()` and produces the most results. SerpAPI and Adzuna are disabled in the current `.env` (keys not set), so JobSpy + Remotive are the two active sources.

### 5. Ollama JSON Mode Difference
For `ollama/` model strings, `response_format={"type":"json_object"}` is NOT sent (Ollama doesn't support it). Instead, `llm_client.py` appends `"Respond with valid JSON only. No explanation."` to the user message content. This is automatic — do not manually add JSON instructions to prompts.

### 6. Ollama May Return JSON Inside Markdown Code Fences
Ollama models sometimes wrap JSON in ```json ... ``` fences despite the instruction. If you see `json.JSONDecodeError` from `cv_scorer.py` or `onboarding.py`, the model is outputting fenced JSON. The current code does NOT strip fences. If this is a recurring issue, add a pre-parse strip:
```python
import re
def strip_fences(text):
    match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    return match.group(1).strip() if match else text
```

### 7. Cache Key Includes Model Name
Changing `MINI_MODEL` in `.env` will cause a full cache miss — all previously cached responses are ignored since the cache key is `SHA256(model + prompt)`. This is intentional for correctness but means switching from `ollama/llama3.2` to `ollama/llama3.1` re-runs all LLM calls.

### 8. Budget Check is Monthly (Calendar Month)
The budget check queries `token_usage` where `timestamp >= start_of_current_month`. It resets automatically on the 1st of each month. With Ollama, `MONTHLY_TOKEN_BUDGET=0` disables this check entirely (`_check_budget()` returns `True` immediately when budget ≤ 0).

### 9. Streamlit Session State
This app does **not use `st.session_state`** for data persistence. All state is stored in the SQLite database. Streamlit page reruns always re-query the DB. UI interactions that modify DB data call `st.rerun()` to refresh the display.

---

## Troubleshooting

### Ollama — "Connection refused" / model not responding
- Make sure `ollama serve` is running in a separate terminal
- Confirm the model is pulled: `ollama list` — you should see `llama3.2`
- If using a non-default port, set `OLLAMA_BASE_URL=http://localhost:<port>` in `.env`
- Test manually: `curl http://localhost:11434/api/tags`

### Ollama — JSON parse errors / `"Could not parse score"`
- The model returned its JSON wrapped in markdown code fences (` ```json ... ``` `)
- Temporary fix: retry — smaller models sometimes output inconsistently
- Permanent fix: add fence-stripping in `services/llm_client.py` before returning `text` (see Known Quirk #6)
- Try a more instruction-following model: `ollama pull mistral` or `ollama pull llama3.1`

### Ollama — slow responses
- `llama3.2` needs ~8GB RAM. If your machine swaps to disk, responses will be slow.
- Switch to a smaller model: `MINI_MODEL=ollama/phi3:mini` or `MINI_MODEL=ollama/gemma2:2b`
- The `time.sleep(4)` in `job_search.py` also adds latency — safe to reduce/remove with Ollama

### JobSpy — "No new jobs found" or empty results
- Check `python-jobspy` is installed: `pip install python-jobspy`
- LinkedIn rate-limits scraping — wait 5-10 minutes and retry
- Try a broader query (e.g., "engineer" instead of a specific role)
- Check `JOBSPY_RESULTS_PER_SITE` in `.env` — setting it too low with many results already in DB may all be duplicates
- Indeed results vary by `country_indeed` — currently auto-detects India vs USA from location string

### "No new jobs found" (general)
- JobSpy + Remotive are always active (no keys needed)
- Remotive is remote-only — try a generic tech query like "developer" or "data"
- Check for duplicates: existing jobs with similar title+company will be skipped

### "Monthly token budget exceeded"
- With Ollama: set `MONTHLY_TOKEN_BUDGET=0` — Ollama is free, no reason to cap it
- With cloud models: increase the budget or check the Dashboard cost breakdown

### "Could not parse score" / JSON decode errors
- Most common with Ollama — see Ollama JSON troubleshooting above
- For cloud models: ensure `MINI_MODEL` supports JSON response format
- Check API key validity and credits

### CV parsing errors
- PDF: requires `pymupdf` (`pip install pymupdf`)
- DOCX: requires `python-docx` (`pip install python-docx`)
- If text extraction is poor (e.g. scanned PDF), convert to plain TXT first

### Database issues
- Delete `data/app.db` to fully reset. All jobs, profile, and cache will be lost.
- Tables are auto-recreated on next `streamlit run app.py`

---

## Extending the Codebase

### Adding a New Job Source
1. Create `services/job_sources/my_source.py`
2. Implement `class MySource(JobSource)` with `async def search(...) -> list[JobResult]`
3. Import and add `MySource()` to the `sources` list in `agents/job_search._fetch_from_all_sources()`
4. Add any required API keys to `config.py` and `.env.example`

### Adding a New Streamlit Page
1. Create `pages/6_My_Page.py` (Streamlit uses filename number prefix for ordering)
2. Follow the pattern: `init_db()` → `db = SessionLocal()` → `try/finally db.close()`
3. Gate with `has_profile(db)` if profile is required

### Adding a New LLM Task
1. Add prompt template to `prompts/my_task.txt`
2. Create an agent file `agents/my_agent.py` with a function that calls `llm_call(task_type="my_task", ...)`
3. Add the new `task_type` string to the dashboard's cost breakdown chart if needed

### Adding Skills to Keyword Detection
Edit the `known_skills` list in `services/cv_parser.extract_skills_keywords()` — it's a simple Python list of lowercase strings.

### Changing LLM Models
Edit `MINI_MODEL` and/or `FULL_MODEL` in your `.env` file. Any litellm-supported model string works. Note: changing models causes a full cache miss (see Known Quirks #6).
