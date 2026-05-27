"""Tests for app.core.cache using fakeredis, including graceful degradation."""

from __future__ import annotations

import numpy as np
import pytest
from fakeredis import FakeRedis

from app.core import cache


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache, "_client", client)
    monkeypatch.setattr(cache, "_stats", {k: 0 for k in cache._stats}, raising=False)
    yield client
    monkeypatch.setattr(cache, "_client", None)


def test_image_embedding_roundtrip_and_stats():
    vec = np.arange(cache_dim := 512, dtype=np.float32) / cache_dim
    image_bytes = b"\x89PNG fake image bytes"

    assert cache.get_cached_image_embedding(image_bytes) is None
    cache.set_cached_image_embedding(image_bytes, vec)
    got = cache.get_cached_image_embedding(image_bytes)

    assert got is not None
    assert np.array_equal(got, vec)
    stats = cache.cache_stats()
    assert stats["image_misses"] == 1
    assert stats["image_hits"] == 1


def test_text_embedding_roundtrip():
    vec = np.ones(512, dtype=np.float32)
    assert cache.get_cached_text_embedding("blue bottle") is None
    cache.set_cached_text_embedding("blue bottle", vec)
    assert np.array_equal(cache.get_cached_text_embedding("blue bottle"), vec)


def test_text_cache_keys_are_content_specific():
    cache.set_cached_text_embedding("alpha", np.zeros(512, dtype=np.float32))
    assert cache.get_cached_text_embedding("beta") is None


def test_llm_roundtrip_keyed_on_payload():
    payload = {"model": "flash", "prompt": "hi", "n": 1}
    response = {"text": "hello", "tokens": 3}

    assert cache.get_cached_llm(payload) is None
    cache.set_cached_llm(payload, response)
    assert cache.get_cached_llm(payload) == response
    # Key is order-independent (canonical JSON with sorted keys).
    assert cache.get_cached_llm({"n": 1, "prompt": "hi", "model": "flash"}) == response


def test_llm_miss_on_different_payload():
    cache.set_cached_llm({"a": 1}, {"text": "x"})
    assert cache.get_cached_llm({"a": 2}) is None


def test_graceful_degradation_on_redis_failure(monkeypatch):
    class BrokenRedis:
        def get(self, *a, **k):
            raise ConnectionError("redis down")

        def set(self, *a, **k):
            raise ConnectionError("redis down")

    monkeypatch.setattr(cache, "_client", BrokenRedis())
    vec = np.ones(512, dtype=np.float32)

    # No exception should escape; set is a no-op, get reports a miss.
    cache.set_cached_image_embedding(b"x", vec)
    assert cache.get_cached_image_embedding(b"x") is None
    assert cache.cache_stats()["image_misses"] >= 1


def test_embed_text_served_from_cache_on_second_call(monkeypatch):
    from app.core import embeddings

    monkeypatch.setattr(cache, "_client", FakeRedis())
    text = "a uniquely phrased cache-wiring probe for embeddings"

    before = embeddings.inference_count()
    v1 = embeddings.embed_text(text)
    after_first = embeddings.inference_count()
    v2 = embeddings.embed_text(text)
    after_second = embeddings.inference_count()

    assert after_first > before  # first call ran inference
    assert after_second == after_first  # second call served from cache
    assert np.array_equal(v1, v2)


def test_embed_image_served_from_cache_on_second_call(monkeypatch):
    from io import BytesIO

    from PIL import Image

    from app.core import embeddings

    monkeypatch.setattr(cache, "_client", FakeRedis())
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(123, 222, 64)).save(buf, format="PNG")
    image_bytes = buf.getvalue()

    before = embeddings.inference_count()
    v1 = embeddings.embed_image(image_bytes)
    after_first = embeddings.inference_count()
    v2 = embeddings.embed_image(image_bytes)
    after_second = embeddings.inference_count()

    assert after_first > before
    assert after_second == after_first
    assert np.array_equal(v1, v2)
