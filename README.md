# Job Search Agent Dashboard

An AI-powered job search agent with a Streamlit dashboard that searches for jobs across multiple sources, scores your CV against openings, and rewrites your CV for maximum conversion — all while minimizing LLM token costs.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Architecture](#architecture)
- [Token Optimization](#token-optimization)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Features

### Job Search
- **Multi-source search** across SerpAPI (Google Jobs), Adzuna, Remotive, and a web scraping fallback
- **Automatic deduplication** using fuzzy string matching (rapidfuzz) — no LLM tokens wasted
- **LLM-powered summaries** of job descriptions (3 bullet points, max 100 words) using a mini model

### CV Management
- **Upload CV** in PDF, DOCX, or TXT format
- **Rule-based parsing** extracts text, sections, and skills keywords — zero LLM tokens
- **One-time LLM structuring** extracts skills, experience level, and education into JSON for reuse

### CV Scoring
- **Batch scoring** — scores up to 5 jobs per LLM call, reducing per-job token overhead by ~40%
- **Rule-based pre-filtering** — jobs with <20% keyword overlap are marked low-match without calling an LLM
- **Cached results** — re-scoring the same CV against the same job costs zero tokens

### CV Rewriting
- **On-demand only** — uses a capable model (Sonnet/GPT-4o) only when you explicitly request a rewrite
- **Job-tailored output** — reorders experience, mirrors job keywords, maintains truthfulness
- **Downloadable** — rewritten CVs saved as Markdown with download option

### Application Tracking
- Track jobs through a pipeline: **New** → **Saved** → **Applied** → **Interviewing** → **Rejected**
- Filter and sort by score, status, or date
- Dashboard with pipeline stats and cost tracking

### Token Cost Control
- **Monthly budget cap** with hard stop when exceeded
- **Per-task cost tracking** with breakdown by task type
- **Model tiering** — cheap models for 95% of tasks, expensive models only for rewrites

---

## Screenshots

Once running, the dashboard provides 5 pages:

| Page | Description |
|---|---|
| **Dashboard** | Stats cards, job pipeline chart, token usage breakdown, top matches |
| **Onboarding** | 5-step profile wizard: upload CV, set roles, locations, salary, projects |
| **Job Search** | Search across all sources, filter/sort results, score and save jobs |
| **My Jobs** | Tabbed view of saved/applied/interviewing/rejected jobs with status actions |
| **CV Manager** | Score CV against specific jobs, trigger rewrites, download tailored CVs |

---

## Quick Start

### Prerequisites

- Python 3.10+
- At least one LLM API key (OpenAI or Anthropic)
- Optionally, a job search API key (SerpAPI, Adzuna) — Remotive works without a key

### Installation

```bash
# Clone the repository
git clone https://github.com/aswinsasidhar25-maker/job-application-agent.git
cd job-application-agent

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your API keys (see Configuration section below)

# Run the dashboard
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

---

## Configuration

All configuration is managed via environment variables in a `.env` file. Copy `.env.example` to get started:

### LLM Provider (set at least one)

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | One of these |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | One of these |

### Job Search Sources

| Variable | Description | Required |
|---|---|---|
| `SERPAPI_API_KEY` | SerpAPI key for Google Jobs search | Optional |
| `ADZUNA_APP_ID` | Adzuna application ID | Optional |
| `ADZUNA_APP_KEY` | Adzuna application key | Optional |
| *(Remotive)* | Free API, no key needed | Always available |

### Model Configuration

| Variable | Default | Description |
|---|---|---|
| `MINI_MODEL` | `gpt-4o-mini` | Cheap model for scoring, summarization, extraction |
| `FULL_MODEL` | `gpt-4o` | Capable model for CV rewriting |
| `MONTHLY_TOKEN_BUDGET` | `10.0` | Monthly spending cap in USD (0 = unlimited) |
| `DATABASE_URL` | `sqlite:///data/app.db` | Database connection string |

### Example `.env`

```env
OPENAI_API_KEY=sk-...
SERPAPI_API_KEY=...
MINI_MODEL=gpt-4o-mini
FULL_MODEL=gpt-4o
MONTHLY_TOKEN_BUDGET=5.0
```

To use Claude models instead:

```env
ANTHROPIC_API_KEY=sk-ant-...
MINI_MODEL=claude-haiku-4-5-20251001
FULL_MODEL=claude-sonnet-4-20250514
```

---

## Usage Guide

### 1. Onboarding (First-Time Setup)

Navigate to the **Onboarding** page and complete 5 steps:

1. **Upload your CV** — PDF, DOCX, or TXT. Text is extracted locally (no LLM call). Skills are detected via keyword matching.
2. **Enter your details** — Name, email, phone, location, salary expectations
3. **Define target roles** — One role per line (e.g., "Software Engineer", "Backend Developer")
4. **Set location preferences** — Preferred cities or "Remote"
5. **Describe your projects** — 2-3 sentences about your most impactful work

A single mini-model LLM call structures your profile at the end (~500 tokens, ~$0.0001).

### 2. Searching for Jobs

Go to the **Job Search** page:

- Leave the search box empty to search using your profile preferences (roles + locations)
- Or enter a custom query and location
- Click **Search Jobs** — the agent queries all configured sources in parallel
- New jobs are deduplicated, summarized, and stored in the database

### 3. Scoring Jobs

- Click **Score Unscored Jobs** to batch-score all new jobs against your CV
- Jobs with <20% keyword overlap are auto-scored without an LLM call
- Remaining jobs are scored in batches of 5 per LLM call
- Each job shows a 0-100 score, matching skills, and skill gaps

### 4. Managing Applications

- Use the action buttons on each job card to **Save**, **Mark Applied**, or **Dismiss**
- The **My Jobs** page shows tabs for each pipeline stage
- Move jobs between stages as your application progresses

### 5. Rewriting Your CV

On the **CV Manager** page:

- Select a job from the dropdown
- Click **Score My CV** to see match analysis
- Click **Rewrite CV for This Job** to generate a tailored version
- The rewritten CV mirrors job keywords, reorders relevant experience, and maintains truthfulness
- Download the result as Markdown

---

## Architecture

### Design Principles

1. **No autonomous agent loop** — The orchestrator (`agents/orchestrator.py`) is pure Python dispatch logic. It never calls an LLM. Every LLM call is triggered by a specific user action. This is the single biggest token saver.

2. **Rule-based first, LLM last** — CV text extraction, deduplication, skill detection, and job filtering all use rule-based approaches. LLMs are only called when structured heuristics won't suffice.

3. **Model tiering** — 95% of LLM calls use a mini model (Haiku/GPT-4o-mini). Only CV rewriting uses a full model (Sonnet/GPT-4o).

4. **Cache everything** — Every LLM response is cached by `SHA256(model + prompt)`. Identical requests cost zero tokens.

### Data Flow

```
User Action → Orchestrator (Python dispatch) → Agent (scoped LLM call) → Result

Example: "Score my CV against this job"
  1. Orchestrator checks for cached score → hit? return cached
  2. Pre-filter: keyword overlap < 20%? → return rule-based score
  3. Call cv_scorer with mini model → ~650 tokens
  4. Cache result → future calls are free
```

### Database Schema

| Table | Purpose |
|---|---|
| `user_profiles` | Name, skills, preferences, parsed CV text, structured CV JSON |
| `jobs` | Title, company, description, summary, requirements, score, status |
| `llm_cache` | SHA256 prompt hash → cached response, with TTL |
| `token_usage` | Per-call token counts and cost, for budget tracking |

---

## Token Optimization

### Cost Breakdown by Operation

| Operation | Model | Tokens/Call | Cost/Call | Frequency |
|---|---|---|---|---|
| Job summarization | Mini | ~400 | $0.0001 | Per new job |
| CV scoring (single) | Mini | ~650 | $0.0001 | Per job |
| CV scoring (batch of 5) | Mini | ~1800 | $0.0003 | Per 5 jobs |
| Profile extraction | Mini | ~500 | $0.0001 | Once at onboarding |
| CV rewriting | Full | ~3500 | $0.03 | On-demand |

### Strategies Ranked by Impact

| # | Strategy | How It Works |
|---|---|---|
| 1 | **No agent loop** | Orchestrator is pure Python — no "think about what to do next" LLM calls |
| 2 | **Model tiering** | Mini model for 95% of calls, full model only for rewrites |
| 3 | **Semantic caching** | SHA256 prompt hashing, 100% hit on identical requests |
| 4 | **Rule-based parsing** | CV extraction, dedup, skill detection, filtering — all zero tokens |
| 5 | **Pre-filtering** | Keyword overlap <20% skips LLM scoring entirely (saves 30-50% of calls) |
| 6 | **Batch scoring** | 5 jobs per call, amortizes system prompt + CV context (~40% savings) |
| 7 | **Prompt compression** | Job descriptions summarized to ~200 words; CV reduced to structured JSON |
| 8 | **Budget cap** | Hard stop when monthly spending limit reached |

### Estimated Monthly Cost

For a typical job search (100 jobs found, 20 rewrites):

| Task | Calls | Cost |
|---|---|---|
| Job summaries | 100 | $0.01 |
| CV scoring | 100 (20 batches) | $0.006 |
| CV rewrites | 20 | $0.60 |
| Profile extraction | 1 | $0.0001 |
| **Total** | | **~$0.62/month** |

---

## Project Structure

```
job-application-agent/
├── app.py                        # Streamlit entry point
├── config.py                     # Settings from environment variables
├── database.py                   # SQLAlchemy engine + session + init
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .gitignore                    # Ignores data/, .env, __pycache__
│
├── models/                       # SQLAlchemy ORM models
│   ├── user.py                   # UserProfile (name, skills, CV, preferences)
│   ├── job.py                    # Job (title, company, score, status)
│   └── cache.py                  # LLMCache + TokenUsage
│
├── agents/                       # LLM-powered agents (scoped, single-task)
│   ├── orchestrator.py           # Pure Python dispatch — NO LLM calls
│   ├── onboarding.py             # CV processing + profile extraction
│   ├── job_search.py             # Multi-source search + summarization
│   ├── cv_scorer.py              # Batched scoring with pre-filtering
│   └── cv_rewriter.py            # CV tailoring (full model)
│
├── services/                     # Business logic (non-agent)
│   ├── llm_client.py             # litellm wrapper + caching + token tracking
│   ├── cache.py                  # Semantic cache (SHA256 prompt hashing)
│   ├── cv_parser.py              # PDF/DOCX text extraction (rule-based)
│   └── job_sources/              # Job board integrations
│       ├── base.py               # JobResult dataclass + JobSource interface
│       ├── serpapi_source.py      # Google Jobs via SerpAPI
│       ├── adzuna_source.py       # Adzuna API
│       ├── remotive_source.py     # Remotive API (free)
│       └── scraper.py            # Web scraping fallback
│
├── prompts/                      # Minimal prompt templates
│   ├── score_cv.txt              # ~50 tokens
│   ├── rewrite_cv.txt            # ~60 tokens
│   ├── summarize_job.txt         # ~40 tokens
│   └── extract_profile.txt       # ~40 tokens
│
├── pages/                        # Streamlit UI pages
│   ├── 1_Dashboard.py            # Stats, pipeline chart, token usage
│   ├── 2_Onboarding.py           # 5-step profile setup wizard
│   ├── 3_Job_Search.py           # Search, filter, score, save
│   ├── 4_My_Jobs.py              # Application pipeline tracking
│   └── 5_CV_Manager.py           # Score + rewrite CV per job
│
├── data/                         # Runtime data (gitignored)
│   ├── app.db                    # SQLite database
│   └── uploads/                  # Uploaded + rewritten CVs
│
└── tests/                        # Test files
```

---

## API Reference

### Job Sources

| Source | API | Free Tier | Key Required |
|---|---|---|---|
| **SerpAPI** | Google Jobs engine | 100 searches/month | Yes |
| **Adzuna** | REST API | 250 requests/day | Yes |
| **Remotive** | REST API | Unlimited | No |
| **Web Scraper** | Google search | N/A (fragile) | No |

### LLM Providers (via litellm)

Any model supported by [litellm](https://docs.litellm.ai/docs/providers) works. Common options:

| Provider | Mini Model | Full Model |
|---|---|---|
| OpenAI | `gpt-4o-mini` | `gpt-4o` |
| Anthropic | `claude-haiku-4-5-20251001` | `claude-sonnet-4-20250514` |
| Local (Ollama) | `ollama/llama3` | `ollama/llama3:70b` |

---

## Troubleshooting

### "No new jobs found"
- Check that at least one job source API key is configured in `.env`
- Remotive works without a key — try searching for "developer" to test
- Check the search query matches actual job titles

### "Monthly token budget exceeded"
- Increase `MONTHLY_TOKEN_BUDGET` in `.env`, or set to `0` for unlimited
- Check the Dashboard page to see cost breakdown by task type

### "Could not parse score"
- This usually means the LLM returned non-JSON output
- Ensure `MINI_MODEL` is set to a model that supports JSON response format
- Check your API key is valid and has credits

### Database issues
- The SQLite database is stored at `data/app.db`
- To reset, delete the file and restart — tables are auto-created

### CV parsing errors
- PDF: Requires `pymupdf` — ensure it installed correctly (`pip install pymupdf`)
- DOCX: Requires `python-docx` — ensure it installed correctly
- If text extraction is poor, try converting your CV to TXT first
