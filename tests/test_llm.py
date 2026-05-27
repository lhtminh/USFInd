"""Tests for app.core.llm with a mocked Gemini SDK (no network)."""

from __future__ import annotations

import pytest
from fakeredis import FakeRedis
from google.api_core import exceptions as gexc

from app.core import cache, llm


class _Usage:
    def __init__(self, prompt_tokens: int, output_tokens: int) -> None:
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = output_tokens


class _Resp:
    def __init__(self, text: str, prompt_tokens: int = 10, output_tokens: int = 5) -> None:
        self.text = text
        self.usage_metadata = _Usage(prompt_tokens, output_tokens)


@pytest.fixture
def fake_gemini(monkeypatch):
    state = {"calls": 0, "responses": []}

    class FakeModel:
        def __init__(self, model_name, system_instruction=None):
            self.model_name = model_name

        def generate_content(self, parts, generation_config=None, request_options=None):
            state["calls"] += 1
            item = state["responses"].pop(0)
            if isinstance(item, Exception):
                raise item
            return item

    monkeypatch.setattr(llm.genai, "GenerativeModel", FakeModel)
    monkeypatch.setattr(llm.time, "sleep", lambda *_: None)
    return state


def test_estimate_cost():
    assert llm.estimate_cost(llm.FLASH_MODEL, 1_000_000, 1_000_000) == pytest.approx(0.375)
    assert llm.estimate_cost(llm.PRO_MODEL, 1_000_000, 0) == pytest.approx(1.25)
    assert llm.estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_call_flash_returns_text(fake_gemini):
    fake_gemini["responses"] = [_Resp("hello world")]
    assert llm.call_flash(["hi"]) == {"text": "hello world"}
    assert fake_gemini["calls"] == 1


def test_call_pro_with_schema_parses_json(fake_gemini):
    fake_gemini["responses"] = [_Resp('{"x": 7}')]
    out = llm.call_pro(["q"], response_schema={"type": "object"})
    assert out == {"x": 7}


def test_invalid_json_raises_llmerror(fake_gemini):
    fake_gemini["responses"] = [_Resp("definitely not json")]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"], response_schema={"type": "object"})


def test_retries_transient_then_succeeds(fake_gemini):
    fake_gemini["responses"] = [
        gexc.ServiceUnavailable("503"),
        gexc.ResourceExhausted("429"),
        _Resp("recovered"),
    ]
    assert llm.call_flash(["q"]) == {"text": "recovered"}
    assert fake_gemini["calls"] == 3


def test_retries_exhausted_raises_llmerror(fake_gemini):
    fake_gemini["responses"] = [gexc.ServiceUnavailable(str(i)) for i in range(3)]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"])
    assert fake_gemini["calls"] == llm.MAX_ATTEMPTS


def test_non_retryable_error_raises_immediately(fake_gemini):
    fake_gemini["responses"] = [ValueError("boom")]
    with pytest.raises(llm.LLMError):
        llm.call_flash(["q"])
    assert fake_gemini["calls"] == 1


def test_cached_call_flash_skips_second_invocation(fake_gemini, monkeypatch):
    monkeypatch.setattr(cache, "_client", FakeRedis())
    fake_gemini["responses"] = [_Resp("cache me")]

    first = llm.cached_call_flash(["same prompt"])
    second = llm.cached_call_flash(["same prompt"])

    assert first == second == {"text": "cache me"}
    assert fake_gemini["calls"] == 1  # second served from cache
