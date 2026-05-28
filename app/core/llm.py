"""LLM client wrappers — OpenRouter (OpenAI-compatible) backend.

Public surface is unchanged from the old Gemini implementation: ``call_flash``,
``call_pro``, and their ``cached_*`` variants. Two model tiers are configurable
via env vars (``OPENROUTER_FLASH_MODEL`` / ``OPENROUTER_PRO_MODEL``) and default
to free, vision-capable models on OpenRouter. Mixed text + PIL image parts are
supported by encoding images as base64 data URLs.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from PIL import Image

from app.core import cache, db
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
FLASH_MODEL = _settings.openrouter_flash_model
PRO_MODEL = _settings.openrouter_pro_model
REQUEST_TIMEOUT = 60
MAX_ATTEMPTS = 3

# Free-tier OpenRouter models cost nothing; override via env when on paid models.
_PRICING: dict[str, tuple[float, float]] = {
    FLASH_MODEL: (0.0, 0.0),
    PRO_MODEL: (0.0, 0.0),
}

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


_client = OpenAI(
    api_key=_settings.openrouter_api_key,
    base_url=_settings.openrouter_base_url,
    timeout=REQUEST_TIMEOUT,
    default_headers={
        # OpenRouter recommends these for free-tier rate-limit attribution.
        "HTTP-Referer": "https://github.com/lhtminh/USFInd",
        "X-Title": "USFind",
    },
)


class LLMError(Exception):
    """Raised when an LLM call fails or returns unusable output."""


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the USD cost of a call from token counts and per-model pricing."""
    input_rate, output_rate = _PRICING.get(model_name, (0.0, 0.0))
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


def _log_usage(
    endpoint: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    cache_hit: bool,
) -> None:
    """Record one row in llm_usage; never raises (telemetry must not break flow)."""
    try:
        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_usage
                  (model, input_tokens, output_tokens, cost_usd, latency_ms, cache_hit, endpoint)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimate_cost(model_name, input_tokens, output_tokens),
                    latency_ms,
                    cache_hit,
                    endpoint,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("Failed to log llm_usage row (%s): %s", endpoint, exc)


def _encode_image(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _build_messages(
    parts: list, system_instruction: str | None, response_schema: dict | None
) -> list[dict]:
    """Translate the legacy text+image parts list into OpenAI chat messages."""
    messages: list[dict] = []
    system_text = (system_instruction or "").strip()
    if response_schema is not None:
        schema_hint = (
            "Respond with ONLY a single valid JSON object that matches this schema. "
            "Do not wrap the JSON in markdown fences or include any prose:\n"
            + json.dumps(response_schema)
        )
        system_text = f"{system_text}\n\n{schema_hint}" if system_text else schema_hint
    if system_text:
        messages.append({"role": "system", "content": system_text})

    content: list[dict] = []
    for part in parts:
        if isinstance(part, str):
            content.append({"type": "text", "text": part})
        elif isinstance(part, Image.Image):
            content.append({"type": "image_url", "image_url": {"url": _encode_image(part)}})
        else:
            content.append({"type": "text", "text": str(part)})
    messages.append({"role": "user", "content": content})
    return messages


def _chat_completion(**kwargs: Any):
    """Thin wrapper around the OpenAI client — single seam for test mocking."""
    return _client.chat.completions.create(**kwargs)


def _call(
    model_name: str,
    parts: list,
    system_instruction: str | None,
    response_schema: dict | None,
    max_output_tokens: int,
    endpoint: str = "unknown",
) -> dict:
    """Invoke an OpenRouter model with retry, then parse and return the response."""
    messages = _build_messages(parts, system_instruction, response_schema)
    kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_output_tokens,
    }
    if response_schema is not None:
        kwargs["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        start = time.perf_counter()
        try:
            response = _chat_completion(**kwargs)
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == MAX_ATTEMPTS:
                break
            delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
            logger.warning(
                "OpenRouter %s transient error (attempt %d/%d): %s; retrying in %ds",
                model_name,
                attempt,
                MAX_ATTEMPTS,
                exc,
                delay,
            )
            time.sleep(delay)
            continue
        except APIError as exc:
            raise LLMError(f"OpenRouter {model_name} call failed: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"OpenRouter {model_name} call failed: {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        cost = estimate_cost(model_name, input_tokens, output_tokens)
        logger.info(
            "LLM call model=%s input_tokens=%d output_tokens=%d latency_ms=%.0f cost_usd=%.6f",
            model_name,
            input_tokens,
            output_tokens,
            latency_ms,
            cost,
        )
        _log_usage(endpoint, model_name, input_tokens, output_tokens, int(latency_ms), False)
        return _parse(response, response_schema, model_name)

    raise LLMError(
        f"OpenRouter {model_name} failed after {MAX_ATTEMPTS} attempts: {last_exc}"
    ) from last_exc


def _parse(response: object, response_schema: dict | None, model_name: str) -> dict:
    try:
        text = response.choices[0].message.content  # type: ignore[attr-defined]
    except (AttributeError, IndexError) as exc:
        raise LLMError(f"{model_name} returned a malformed response") from exc
    if text is None:
        raise LLMError(f"{model_name} returned no content")
    if response_schema is None:
        return {"text": text}
    return _extract_json(text, model_name)


def _extract_json(text: str, model_name: str) -> dict:
    """Best-effort parse: handles raw JSON, code-fenced JSON, and surrounding prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fall back: take the largest brace-balanced span.
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"{model_name} returned invalid JSON: {exc}") from exc
    raise LLMError(f"{model_name} returned non-JSON content for a schema request")


def call_flash(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 1024,
    endpoint: str = "unknown",
) -> dict:
    """Call the configured "flash" model for cheap text/vision tasks."""
    return _call(
        FLASH_MODEL, parts, system_instruction, response_schema, max_output_tokens, endpoint
    )


def call_pro(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 2048,
    endpoint: str = "unknown",
) -> dict:
    """Call the configured "pro" model for high-quality reasoning such as re-ranking."""
    return _call(PRO_MODEL, parts, system_instruction, response_schema, max_output_tokens, endpoint)


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
    endpoint: str = "unknown",
) -> dict:
    """Cached flash-tier call keyed on a content hash of the prompt."""
    payload = _cache_payload(
        FLASH_MODEL, parts, system_instruction, response_schema, max_output_tokens
    )
    cached = cache.get_cached_llm(payload)
    if cached is not None:
        _log_usage(endpoint, FLASH_MODEL, 0, 0, 0, True)
        return cached
    result = call_flash(
        parts, system_instruction, response_schema, max_output_tokens, endpoint=endpoint
    )
    cache.set_cached_llm(payload, result)
    return result


def cached_call_pro(
    parts: list,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
    max_output_tokens: int = 2048,
    endpoint: str = "unknown",
) -> dict:
    """Cached pro-tier call keyed on a content hash of the prompt."""
    payload = _cache_payload(
        PRO_MODEL, parts, system_instruction, response_schema, max_output_tokens
    )
    cached = cache.get_cached_llm(payload)
    if cached is not None:
        _log_usage(endpoint, PRO_MODEL, 0, 0, 0, True)
        return cached
    result = call_pro(
        parts, system_instruction, response_schema, max_output_tokens, endpoint=endpoint
    )
    cache.set_cached_llm(payload, result)
    return result
