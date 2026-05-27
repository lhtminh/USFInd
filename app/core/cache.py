"""Redis caching for embeddings and LLM responses.

Three logical caches share one Redis instance, keyed by content hash:
``emb:img:<sha>`` and ``emb:txt:<sha>`` hold pickled vectors; ``llm:<sha>``
holds JSON responses. Every Redis call degrades gracefully — on failure it logs
a warning and behaves as a cache miss, so the app keeps working without Redis.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import threading

import numpy as np
import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMB_TTL = 30 * 24 * 3600  # 30 days
LLM_TTL = 7 * 24 * 3600  # 7 days

_client: redis.Redis | None = None
_client_lock = threading.Lock()

_stats: dict[str, int] = {
    "image_hits": 0,
    "image_misses": 0,
    "text_hits": 0,
    "text_misses": 0,
    "llm_hits": 0,
    "llm_misses": 0,
}
_stats_lock = threading.Lock()


def get_client() -> redis.Redis:
    """Return the lazily-created, process-wide Redis client (binary mode)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = redis.Redis.from_url(get_settings().redis_url, decode_responses=False)
    return _client


def _bump(stat: str) -> None:
    with _stats_lock:
        _stats[stat] += 1


def cache_stats() -> dict[str, int]:
    """Return a snapshot of per-cache hit/miss counters since process start."""
    with _stats_lock:
        return dict(_stats)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get(key: str) -> bytes | None:
    try:
        return get_client().get(key)
    except Exception as exc:
        logger.warning("Redis GET failed for %s: %s", key, exc)
        return None


def _set(key: str, value: bytes, ttl: int) -> None:
    try:
        get_client().set(key, value, ex=ttl)
    except Exception as exc:
        logger.warning("Redis SET failed for %s: %s", key, exc)


def get_cached_image_embedding(image_bytes: bytes) -> np.ndarray | None:
    """Return a cached image embedding for these bytes, or None on miss/failure."""
    raw = _get(f"emb:img:{_sha(image_bytes)}")
    if raw is None:
        _bump("image_misses")
        return None
    try:
        vector = pickle.loads(raw)
    except Exception as exc:
        logger.warning("Failed to decode cached image embedding: %s", exc)
        _bump("image_misses")
        return None
    _bump("image_hits")
    return vector


def set_cached_image_embedding(image_bytes: bytes, vector: np.ndarray) -> None:
    """Cache an image embedding keyed by the image content hash."""
    payload = pickle.dumps(np.asarray(vector, dtype=np.float32))
    _set(f"emb:img:{_sha(image_bytes)}", payload, EMB_TTL)


def get_cached_text_embedding(text: str) -> np.ndarray | None:
    """Return a cached text embedding for this text, or None on miss/failure."""
    raw = _get(f"emb:txt:{_sha(text.encode('utf-8'))}")
    if raw is None:
        _bump("text_misses")
        return None
    try:
        vector = pickle.loads(raw)
    except Exception as exc:
        logger.warning("Failed to decode cached text embedding: %s", exc)
        _bump("text_misses")
        return None
    _bump("text_hits")
    return vector


def set_cached_text_embedding(text: str, vector: np.ndarray) -> None:
    """Cache a text embedding keyed by the text content hash."""
    payload = pickle.dumps(np.asarray(vector, dtype=np.float32))
    _set(f"emb:txt:{_sha(text.encode('utf-8'))}", payload, EMB_TTL)


def _llm_key(prompt_payload: dict) -> str:
    canonical = json.dumps(prompt_payload, sort_keys=True, default=str).encode("utf-8")
    return f"llm:{_sha(canonical)}"


def get_cached_llm(prompt_payload: dict) -> dict | None:
    """Return a cached LLM response for this prompt payload, or None on miss."""
    raw = _get(_llm_key(prompt_payload))
    if raw is None:
        _bump("llm_misses")
        return None
    try:
        response = json.loads(raw)
    except Exception as exc:
        logger.warning("Failed to decode cached LLM response: %s", exc)
        _bump("llm_misses")
        return None
    _bump("llm_hits")
    return response


def set_cached_llm(prompt_payload: dict, response: dict) -> None:
    """Cache an LLM response keyed by a canonical hash of the prompt payload."""
    _set(_llm_key(prompt_payload), json.dumps(response).encode("utf-8"), LLM_TTL)
