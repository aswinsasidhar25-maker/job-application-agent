from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from litellm import completion
from litellm.exceptions import RateLimitError
from sqlalchemy.orm import Session
from config import settings
from models.cache import TokenUsage
from services.cache import get_cached_response, set_cached_response

# Approximate cost per 1M tokens (input, output) by model pattern
COST_MAP = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku": (0.25, 1.25),
    "claude-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
}


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    for pattern, (cost_in, cost_out) in COST_MAP.items():
        if pattern in model.lower():
            return (tokens_in * cost_in + tokens_out * cost_out) / 1_000_000
    return (tokens_in * 1.0 + tokens_out * 3.0) / 1_000_000  # fallback


def _check_budget(db: Session) -> bool:
    if settings.MONTHLY_TOKEN_BUDGET <= 0:
        return True
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(TokenUsage).filter(TokenUsage.timestamp >= start_of_month).all()
    total = sum(r.cost_usd for r in rows)
    return total < settings.MONTHLY_TOKEN_BUDGET


def _log_usage(
    db: Session, task_type: str, model: str, tokens_in: int, tokens_out: int
):
    cost = _estimate_cost(model, tokens_in, tokens_out)
    usage = TokenUsage(
        task_type=task_type,
        model=model,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        cost_usd=cost,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(usage)
    db.commit()


def llm_call(
    db: Session,
    prompt: str,
    task_type: str = "general",
    system: str = "",
    model: str | None = None,
    use_cache: bool = True,
    cache_ttl: int = 720,
    json_mode: bool = True,
) -> str:
    """Make an LLM call with caching and token tracking.

    Args:
        db: Database session
        prompt: User prompt
        task_type: For token tracking (score/rewrite/search/onboard/summarize)
        system: System prompt (keep short!)
        model: Override model, defaults to MINI_MODEL
        use_cache: Whether to check/store cache
        cache_ttl: Cache TTL in hours
        json_mode: Request JSON output format
    """
    model = model or settings.MINI_MODEL
    full_prompt = f"{system}\n{prompt}" if system else prompt

    if use_cache:
        cached = get_cached_response(db, model, full_prompt)
        if cached is not None:
            return cached

    if not _check_budget(db):
        return json.dumps({"error": "Monthly token budget exceeded"})

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    is_ollama = model.startswith("ollama/")
    kwargs = {"model": model, "messages": messages, "temperature": 0.3}
    if is_ollama:
        kwargs["api_base"] = settings.OLLAMA_BASE_URL
    # Ollama models use format param, not response_format; only enable json_mode for cloud models
    if json_mode and not is_ollama:
        kwargs["response_format"] = {"type": "json_object"}
    elif json_mode and is_ollama:
        # Ask the model to respond in JSON via the prompt instead
        messages[-1]["content"] += "\n\nRespond with valid JSON only. No explanation."

    # Retry with exponential backoff for rate limit errors (Gemini free tier: 15 RPM)
    for attempt in range(4):
        try:
            response = completion(**kwargs)
            break
        except RateLimitError:
            if attempt == 3:
                return json.dumps({"error": "Rate limit exceeded. Please wait a moment and try again."})
            wait = 5 * (2 ** attempt)  # 5s, 10s, 20s, 40s
            time.sleep(wait)
    else:
        return json.dumps({"error": "Rate limit exceeded after retries."})

    text = response.choices[0].message.content or ""
    tokens_in = response.usage.prompt_tokens if response.usage else 0
    tokens_out = response.usage.completion_tokens if response.usage else 0

    _log_usage(db, task_type, model, tokens_in, tokens_out)

    if use_cache:
        set_cached_response(db, model, full_prompt, text, tokens_in, tokens_out, cache_ttl)

    return text
