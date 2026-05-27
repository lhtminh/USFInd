"""Google Gemini client wrappers with retry, structured output, and cost tracking.

Two model tiers are exposed: ``call_flash`` (gemini-2.0-flash, cheap) and
``call_pro`` (gemini-2.5-pro, used for re-ranking). Both accept mixed text and
PIL image parts, optionally enforce a JSON response schema, retry transient
errors, and log token usage plus an estimated USD cost. ``cached_*`` variants
short-circuit through the Redis LLM cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time

import google.generativeai as genai
from google.api_core import exceptions as gexc
from PIL import Image

from app.core import cache
from app.core.config import get_settings

logger = logging.getLogger(__name__)

FLASH_MODEL = "gemini-2.0-flash"
PRO_MODEL = "gemini-2.5-pro"
REQUEST_TIMEOUT = 60
MAX_ATTEMPTS = 3

# USD per 1M tokens: (input_rate, output_rate).
_PRICING: dict[str, tuple[float, float]] = {
    FLASH_MODEL: (0.075, 0.30),
    PRO_MODEL: (1.25, 5.00),
}

_RETRYABLE = (
    gexc.ResourceExhausted,
    gexc.ServiceUnavailable,
    gexc.InternalServerError,
    gexc.GatewayTimeout,
    gexc.DeadlineExceeded,
)

genai.configure(api_key=get_settings().gemini_api_key)


class LLMError(Exception):
    """Raised when a Gemini call fails or returns unusable output."""


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the USD cost of a call from token counts and per-model pricing."""
    input_rate, output_rate = _PRICING.get(model_name, (0.0, 0.0))
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


def _call(
    model_name: str,
    parts: list,
    system_instruction: str | None,
    response_schema: dict | None,
    max_output_tokens: int,
) -> dict:
    """Invoke a Gemini model with retry, then parse and return the response."""
    generation_config: dict = {"max_output_tokens": max_output_tokens}
    if response_schema is not None:
        generation_config["response_mime_type"] = "application/json"
        generation_config["response_schema"] = response_schema

    model = genai.GenerativeModel(model_name, system_instruction=system_instruction)

    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        start = time.perf_counter()
        try:
            response = model.generate_content(
                parts,
                generation_config=generation_config,
                request_options={"timeout": REQUEST_TIMEOUT},
            )
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == MAX_ATTEMPTS:
                break
            delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
            logger.warning(
                "Gemini %s transient error (attempt %d/%d): %s; retrying in %ds",
                model_name,
                attempt,
                MAX_ATTEMPTS,
                exc,
                delay,
            )
            time.sleep(delay)
            continue
        except Exception as exc:
            raise LLMError(f"Gemini {model_name} call failed: {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        cost = estimate_cost(model_name, input_tokens, output_tokens)
        logger.info(
            "Gemini call model=%s input_tokens=%d output_tokens=%d latency_ms=%.0f cost_usd=%.6f",
            model_name,
            input_tokens,
            output_tokens,
            latency_ms,
            cost,
        )
        return _parse(response, response_schema, model_name)

    raise LLMError(
        f"Gemini {model_name} failed after {MAX_ATTEMPTS} attempts: {last_exc}"
    ) from last_exc


def _parse(response: object, response_schema: dict | None, model_name: str) -> dict:
    text = getattr(response, "text", None)
    if text is None:
        raise LLMError(f"Gemini {model_name} returned no text content")
    if response_schema is None:
        return {"text": text}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Gemini {model_name} returned invalid JSON: {exc}") from exc


def call_flash(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 1024,
) -> dict:
    """Call gemini-2.0-flash for cheap text/vision tasks."""
    return _call(FLASH_MODEL, parts, system_instruction, response_schema, max_output_tokens)


def call_pro(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 2048,
) -> dict:
    """Call gemini-2.5-pro for high-quality reasoning such as re-ranking."""
    return _call(PRO_MODEL, parts, system_instruction, response_schema, max_output_tokens)


def _serialize_parts(parts: list) -> list[dict]:
    """Represent prompt parts as stable, hashable structures for cache keys."""
    serialized: list[dict] = []
    for part in parts:
        if isinstance(part, str):
            serialized.append({"text": part})
        elif isinstance(part, Image.Image):
            digest = hashlib.sha256(part.convert("RGB").tobytes()).hexdigest()
            serialized.append({"image_sha256": digest})
        else:
            serialized.append({"repr": repr(part)})
    return serialized


def _cache_payload(
    model_name: str,
    parts: list,
    system_instruction: str | None,
    response_schema: dict | None,
    max_output_tokens: int,
) -> dict:
    return {
        "model": model_name,
        "system_instruction": system_instruction,
        "response_schema": response_schema,
        "max_output_tokens": max_output_tokens,
        "parts": _serialize_parts(parts),
    }


def cached_call_flash(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 1024,
) -> dict:
    """Cached gemini-2.0-flash call keyed on a content hash of the prompt."""
    payload = _cache_payload(
        FLASH_MODEL, parts, system_instruction, response_schema, max_output_tokens
    )
    cached = cache.get_cached_llm(payload)
    if cached is not None:
        return cached
    result = call_flash(parts, system_instruction, response_schema, max_output_tokens)
    cache.set_cached_llm(payload, result)
    return result


def cached_call_pro(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 2048,
) -> dict:
    """Cached gemini-2.5-pro call keyed on a content hash of the prompt."""
    payload = _cache_payload(
        PRO_MODEL, parts, system_instruction, response_schema, max_output_tokens
    )
    cached = cache.get_cached_llm(payload)
    if cached is not None:
        return cached
    result = call_pro(parts, system_instruction, response_schema, max_output_tokens)
    cache.set_cached_llm(payload, result)
    return result
