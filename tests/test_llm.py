"""Tests for app.core.llm with a mocked OpenAI/OpenRouter client (no network)."""

from __future__ import annotations

import httpx
import pytest
from fakeredis import FakeRedis
from openai import APIConnectionError, RateLimitError

from app.core import cache, llm


class _Usage:
    def __init__(self, prompt_tokens: int, output_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = output_tokens


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Resp:
    def __init__(self, content: str, prompt: int = 10, output: int = 5) -> None:
        self.choices = [_Choice(content)]
        self.usage = _Usage(prompt, output)


def _rate_limit() -> RateLimitError:
    request = httpx.Request("POST", "https://openrouter.test/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("429", response=response, body=None)


def _connection_error() -> APIConnectionError:
    request = httpx.Request("POST", "https://openrouter.test/v1/chat/completions")
    return APIConnectionError(request=request)


@pytest.fixture
def fake_chat(monkeypatch):
    state = {"calls": 0, "responses": []}

    def fake(**kwargs):
        state["calls"] += 1
        item = state["responses"].pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm, "_chat_completion", fake)
    monkeypatch.setattr(llm.time, "sleep", lambda *_: None)
    return state


def test_estimate_cost_returns_zero_for_free_models():
    assert llm.estimate_cost(llm.FLASH_MODEL, 1_000_000, 1_000_000) == 0.0
    assert llm.estimate_cost(llm.PRO_MODEL, 1_000_000, 0) == 0.0
    assert llm.estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_call_flash_returns_text(fake_chat):
    fake_chat["responses"] = [_Resp("hello world")]
    assert llm.call_flash(["hi"]) == {"text": "hello world"}
    assert fake_chat["calls"] == 1


def test_call_pro_with_schema_parses_json(fake_chat):
    fake_chat["responses"] = [_Resp('{"x": 7}')]
    out = llm.call_pro(["q"], response_schema={"type": "object"})
    assert out == {"x": 7}


def test_invalid_json_raises_llmerror(fake_chat):
    fake_chat["responses"] = [_Resp("definitely not json")]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"], response_schema={"type": "object"})


def test_json_extractor_handles_code_fences(fake_chat):
    fake_chat["responses"] = [_Resp('```json\n{"a": 1}\n```')]
    out = llm.call_flash(["q"], response_schema={"type": "object"})
    assert out == {"a": 1}


def test_json_extractor_handles_surrounding_prose(fake_chat):
    fake_chat["responses"] = [_Resp('Sure! Here you go: {"a": 2} thanks!')]
    out = llm.call_flash(["q"], response_schema={"type": "object"})
    assert out == {"a": 2}


def test_retries_transient_then_succeeds(fake_chat):
    fake_chat["responses"] = [
        _connection_error(),
        _rate_limit(),
        _Resp("recovered"),
    ]
    assert llm.call_flash(["q"]) == {"text": "recovered"}
    assert fake_chat["calls"] == 3


def test_retries_exhausted_raises_llmerror(fake_chat):
    fake_chat["responses"] = [_rate_limit() for _ in range(3)]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"])
    assert fake_chat["calls"] == llm.MAX_ATTEMPTS


def test_non_retryable_error_raises_immediately(fake_chat):
    fake_chat["responses"] = [ValueError("boom")]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"])
    assert fake_chat["calls"] == 1


def test_cached_call_flash_skips_second_invocation(fake_chat, monkeypatch):
    monkeypatch.setattr(cache, "_client", FakeRedis())
    fake_chat["responses"] = [_Resp("cache me")]

    first = llm.cached_call_flash(["same prompt"])
    second = llm.cached_call_flash(["same prompt"])

    assert first == second == {"text": "cache me"}
    assert fake_chat["calls"] == 1  # second served from cache
