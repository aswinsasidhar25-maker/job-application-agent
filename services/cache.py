from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.cache import LLMCache


def make_cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def get_cached_response(db: Session, model: str, prompt: str) -> str | None:
    key = make_cache_key(model, prompt)
    entry = db.query(LLMCache).filter(LLMCache.prompt_hash == key).first()
    if not entry:
        return None
    expiry = entry.created_at + timedelta(hours=entry.ttl_hours)
    if datetime.now(timezone.utc) > expiry.replace(tzinfo=timezone.utc):
        db.delete(entry)
        db.commit()
        return None
    return entry.response_text


def set_cached_response(
    db: Session,
    model: str,
    prompt: str,
    response: str,
    tokens_in: int,
    tokens_out: int,
    ttl_hours: int = 720,
):
    key = make_cache_key(model, prompt)
    existing = db.query(LLMCache).filter(LLMCache.prompt_hash == key).first()
    if existing:
        existing.response_text = response
        existing.tokens_input = tokens_in
        existing.tokens_output = tokens_out
        existing.created_at = datetime.now(timezone.utc)
    else:
        entry = LLMCache(
            prompt_hash=key,
            model=model,
            response_text=response,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            ttl_hours=ttl_hours,
        )
        db.add(entry)
    db.commit()
