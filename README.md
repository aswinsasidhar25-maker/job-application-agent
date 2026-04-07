# Job Search Agent Dashboard

An AI-powered job search agent with a Streamlit dashboard that searches for jobs, scores your CV against openings, and rewrites your CV for maximum conversion — all while minimizing LLM token costs.

## Features

- **Multi-Source Job Search**: Searches SerpAPI (Google Jobs), Adzuna, Remotive, and web scraping
- **Smart CV Scoring**: Batched scoring with pre-filtering to minimize API costs
- **CV Rewriting**: AI-powered CV tailoring for specific job postings
- **Token Cost Tracking**: Real-time dashboard showing LLM usage and costs
- **Application Pipeline**: Track jobs through new → saved → applied → interviewing stages

## Token Optimization

This agent is designed to minimize LLM costs:

| Strategy | Savings |
|---|---|
| Rule-based CV parsing (pymupdf) | ~2000 tokens/call |
| Rule-based dedup (rapidfuzz) | ~500 tokens/call |
| Keyword pre-filtering before LLM scoring | 30-50% of jobs skip LLM |
| Batched scoring (5 jobs/call) | ~40% token reduction |
| Semantic caching (SHA256 hashing) | 100% on repeat calls |
| Mini model for scoring/summarizing | 10-50x cheaper than full model |
| Full model only for CV rewriting (on-demand) | ~$0.03/rewrite |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env with your API keys

# 3. Run the dashboard
streamlit run app.py
```

## Required API Keys

Set at least one LLM provider and one job source in `.env`:

- **LLM**: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- **Jobs**: `SERPAPI_API_KEY`, `ADZUNA_APP_ID`+`ADZUNA_APP_KEY`, or use Remotive (free, no key needed)

## Project Structure

```
├── app.py                  # Streamlit entry point
├── config.py               # Settings & API keys
├── database.py             # SQLite + SQLAlchemy
├── models/                 # Database models (User, Job, Cache)
├── agents/                 # LLM agents (search, score, rewrite)
├── services/               # Business logic (CV parser, job sources, LLM client)
├── prompts/                # Minimal prompt templates
├── pages/                  # Streamlit UI pages
└── data/                   # Runtime data (DB, uploads) - gitignored
```
