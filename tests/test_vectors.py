"""Tests for app.core.vectors using Qdrant in-memory mode (no server needed)."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.core import vectors


@pytest.fixture(autouse=True)
def in_memory_qdrant(monkeypatch):
    client = QdrantClient(location=":memory:")
    monkeypatch.setattr(vectors, "_client", client)
    vectors.ensure_collections()
    yield client
    monkeypatch.setattr(vectors, "_client", None)


def _basis(i: int) -> np.ndarray:
    v = np.zeros(vectors.VECTOR_SIZE, dtype=np.float32)
    v[i] = 1.0
    return v


def _payload(item_type: str, status: str = "open", ts: int = 1_700_000_000) -> dict:
    return {"type": item_type, "status": status, "created_at_ts": ts}


def test_upsert_and_get_embeddings_roundtrip():
    item_id = uuid4()
    img, txt = _basis(0), _basis(1)
    vectors.upsert_image_embedding(item_id, img, _payload("lost"))
    vectors.upsert_text_embedding(item_id, txt, _payload("lost"))

    got_img, got_txt = vectors.get_embeddings(item_id)
    assert got_img is not None and got_txt is not None
    assert np.allclose(got_img, img, atol=1e-6)
    assert np.allclose(got_txt, txt, atol=1e-6)


def test_get_embeddings_missing_returns_none():
    assert vectors.get_embeddings(uuid4()) == (None, None)


def test_search_image_orders_by_similarity():
    ids = [uuid4() for _ in range(3)]
    for i, item_id in enumerate(ids):
        vectors.upsert_image_embedding(item_id, _basis(i), _payload("found"))

    results = vectors.search_image(_basis(0), qdrant_filter=None, limit=3)
    assert str(results[0].id) == str(ids[0])
    assert results[0].score == pytest.approx(1.0, abs=1e-5)


def test_search_text_respects_type_filter_and_exclusion():
    lost_id, found_a, found_b = uuid4(), uuid4(), uuid4()
    vectors.upsert_text_embedding(lost_id, _basis(0), _payload("lost"))
    vectors.upsert_text_embedding(found_a, _basis(0), _payload("found"))
    vectors.upsert_text_embedding(found_b, _basis(1), _payload("found"))

    only_found = vectors.build_filter(item_type="found", status="open")
    results = vectors.search_text(_basis(0), qdrant_filter=only_found, limit=10)
    returned = {str(r.id) for r in results}
    assert returned == {str(found_a), str(found_b)}

    excl = vectors.build_filter(item_type="found", exclude_item_id=found_a)
    results2 = vectors.search_text(_basis(0), qdrant_filter=excl, limit=10)
    assert {str(r.id) for r in results2} == {str(found_b)}


def test_build_filter_created_after():
    old_id, new_id = uuid4(), uuid4()
    vectors.upsert_text_embedding(old_id, _basis(0), _payload("found", ts=1000))
    vectors.upsert_text_embedding(new_id, _basis(0), _payload("found", ts=5000))

    flt = vectors.build_filter(created_after_ts=4000)
    results = vectors.search_text(_basis(0), qdrant_filter=flt, limit=10)
    assert {str(r.id) for r in results} == {str(new_id)}


def test_build_filter_returns_none_when_empty():
    assert vectors.build_filter() is None


def test_delete_item_removes_from_both_collections():
    item_id = uuid4()
    vectors.upsert_image_embedding(item_id, _basis(0), _payload("lost"))
    vectors.upsert_text_embedding(item_id, _basis(1), _payload("lost"))

    vectors.delete_item(item_id)
    assert vectors.get_embeddings(item_id) == (None, None)


def test_collection_stats_reports_counts():
    for i in range(2):
        item_id = uuid4()
        vectors.upsert_image_embedding(item_id, _basis(i), _payload("lost"))
    vectors.upsert_text_embedding(uuid4(), _basis(0), _payload("found"))

    stats = vectors.collection_stats()
    assert stats[vectors.COLLECTION_IMAGE]["points_count"] == 2
    assert stats[vectors.COLLECTION_TEXT]["points_count"] == 1
