"""Tests for app.core.retrieval Stage 1 recall (Neon + in-memory Qdrant)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import psycopg
import pytest
from qdrant_client import QdrantClient

from app.core import cache, db, retrieval, vectors
from app.core.config import get_settings


def _db_reachable() -> bool:
    try:
        with psycopg.connect(str(get_settings().database_url), connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(), reason="No Postgres reachable via DATABASE_URL"
)

_RESET_SQL = """
DROP TABLE IF EXISTS matches, items, users, llm_usage, schema_migrations CASCADE;
DROP FUNCTION IF EXISTS set_updated_at() CASCADE;
"""


def _basis(i: int) -> np.ndarray:
    v = np.zeros(vectors.VECTOR_SIZE, dtype=np.float32)
    v[i] = 1.0
    return v


@pytest.fixture(scope="class")
def schema():
    with db.get_conn() as conn:
        conn.execute(_RESET_SQL)
        conn.commit()
    db.run_migrations()
    yield
    with db.get_conn() as conn:
        conn.execute(_RESET_SQL)
        conn.commit()
    db.close_pool()


@pytest.fixture(autouse=True)
def environment(schema, monkeypatch):
    with db.get_conn() as conn:
        conn.execute("TRUNCATE matches, items, users, llm_usage RESTART IDENTITY CASCADE")
        conn.commit()
    monkeypatch.setattr(vectors, "_client", QdrantClient(location=":memory:"))
    vectors.ensure_collections()
    yield
    monkeypatch.setattr(vectors, "_client", None)


def _seed_item(user_id, item_type, image_basis, text_basis, title):
    item = db.insert_item(user_id, item_type, title, None, "u", "k", None)
    ts = int(datetime.now(UTC).timestamp())
    payload = {"type": item_type, "status": "open", "created_at_ts": ts}
    vectors.upsert_image_embedding(item.id, _basis(image_basis), payload)
    vectors.upsert_text_embedding(item.id, _basis(text_basis), payload)
    return item


class TestStage1Recall:
    def test_ordering_filter_threshold_and_type(self):
        user = db.upsert_user("recall@usf.edu", "Rey")
        query = _seed_item(user.id, "lost", 0, 1, "query")
        a = _seed_item(user.id, "found", 0, 1, "A")  # combined 1.0
        b = _seed_item(user.id, "found", 0, 2, "B")  # combined 0.7
        _seed_item(user.id, "found", 2, 2, "C")  # combined 0.0 -> filtered
        _seed_item(user.id, "lost", 0, 1, "D")  # same type -> excluded

        candidates = retrieval.stage1_recall(query.id)

        assert [c.item_id for c in candidates] == [a.id, b.id]
        assert candidates[0].combined_score == pytest.approx(1.0, abs=1e-5)
        assert candidates[1].combined_score == pytest.approx(0.7, abs=1e-5)
        assert candidates[0].stage1_rank == 1
        assert candidates[1].stage1_rank == 2
        assert candidates[0].item.title == "A"

    def test_excludes_query_item_itself(self):
        user = db.upsert_user("self@usf.edu", "Sal")
        # A found item that would match, plus the query of the opposite type.
        query = _seed_item(user.id, "found", 0, 1, "query")
        _seed_item(user.id, "lost", 0, 1, "match")
        results = retrieval.stage1_recall(query.id)
        assert all(c.item_id != query.id for c in results)

    def test_missing_query_raises(self):
        with pytest.raises(retrieval.RetrievalError):
            retrieval.stage1_recall(uuid4())

    def test_missing_embeddings_raises(self):
        user = db.upsert_user("noemb@usf.edu", "Noe")
        item = db.insert_item(user.id, "lost", "no-embeddings", None, "u", "k", None)
        with pytest.raises(retrieval.RetrievalError):
            retrieval.stage1_recall(item.id)


def _candidate(item, combined=0.8):
    return retrieval.Candidate(
        item_id=item.id,
        combined_score=combined,
        image_score=combined,
        text_score=combined,
        item=item,
        stage1_rank=1,
    )


class TestStage2Rerank:
    def test_rerank_filters_below_threshold_and_sorts(self, monkeypatch):
        user = db.upsert_user("rr@usf.edu", "Ree")
        query = db.insert_item(user.id, "lost", "query", None, "u", "k", None)
        a = db.insert_item(user.id, "found", "A", None, "u", "k", None)
        b = db.insert_item(user.id, "found", "B", None, "u", "k", None)
        c = db.insert_item(user.id, "found", "C", None, "u", "k", None)
        candidates = [_candidate(a), _candidate(b), _candidate(c)]

        rankings = [
            {"candidate_index": 1, "rerank_score": 90, "explanation": "exact match"},
            {"candidate_index": 2, "rerank_score": 30, "explanation": "different color"},
            {"candidate_index": 3, "rerank_score": 70, "explanation": "likely match"},
        ]
        monkeypatch.setattr(
            retrieval.llm, "cached_call_pro", lambda *a, **k: {"rankings": rankings}
        )

        result = retrieval.stage2_rerank(query, candidates, top_k=10)

        assert [c.item_id for c in result] == [a.id, c.id]  # B dropped (30 < 40)
        assert result[0].rerank_score == 90
        assert result[0].explanation == "exact match"

    def test_rerank_empty_returns_empty(self):
        user = db.upsert_user("empty@usf.edu", "Emp")
        query = db.insert_item(user.id, "lost", "q", None, "u", "k", None)
        assert retrieval.stage2_rerank(query, [], top_k=10) == []

    def test_full_retrieval_combines_stages(self, monkeypatch):
        user = db.upsert_user("full@usf.edu", "Fud")
        query = _seed_item(user.id, "lost", 0, 1, "query")
        a = _seed_item(user.id, "found", 0, 1, "A")

        monkeypatch.setattr(
            retrieval.llm,
            "cached_call_pro",
            lambda *args, **kwargs: {
                "rankings": [{"candidate_index": 1, "rerank_score": 88, "explanation": "match"}]
            },
        )

        result = retrieval.full_retrieval(query.id, final_k=10)

        assert result.stage1_count >= 1
        assert [c.item_id for c in result.candidates] == [a.id]
        assert result.candidates[0].rerank_score == 88
        assert result.cache_hit is False
        assert result.total_ms >= 0


class TestRerankCache:
    def test_second_full_retrieval_served_from_cache(self, monkeypatch):
        from fakeredis import FakeRedis

        monkeypatch.setattr(cache, "_client", FakeRedis())
        user = db.upsert_user("rcache@usf.edu", "Rca")
        query = _seed_item(user.id, "lost", 0, 1, "query")
        a = _seed_item(user.id, "found", 0, 1, "A")

        calls = {"n": 0}

        def fake_pro(*args, **kwargs):
            calls["n"] += 1
            return {
                "rankings": [{"candidate_index": 1, "rerank_score": 80, "explanation": "match"}]
            }

        monkeypatch.setattr(retrieval.llm, "cached_call_pro", fake_pro)

        first = retrieval.full_retrieval(query.id)
        second = retrieval.full_retrieval(query.id)

        assert first.cache_hit is False
        assert second.cache_hit is True
        assert calls["n"] == 1  # Stage 2 ran once; second call hit the cache
        assert [c.item_id for c in second.candidates] == [a.id]
        assert second.candidates[0].rerank_score == 80

        stats = cache.cache_stats()
        assert stats["rerank_hits"] >= 1
        assert stats["rerank_misses"] >= 1


class TestConversationalSearch:
    def test_text_recall_then_rerank(self, monkeypatch):
        user = db.upsert_user("conv@usf.edu", "Con")
        a = _seed_item(user.id, "lost", 0, 0, "A")  # text vec e0 -> score 1.0
        _seed_item(user.id, "lost", 0, 1, "B")  # text vec e1 -> score 0 (below threshold)
        _seed_item(user.id, "found", 0, 0, "C")  # opposite-type filter excludes it

        # search_type "found" means the user found something -> look at lost items.
        parsed = retrieval.ParsedSearch(semantic_query="anything", search_type="found")
        monkeypatch.setattr(retrieval.embeddings, "embed_text", lambda _: _basis(0))
        monkeypatch.setattr(
            retrieval.llm,
            "cached_call_pro",
            lambda *args, **kwargs: {
                "rankings": [{"candidate_index": 1, "rerank_score": 70, "explanation": "a"}]
            },
        )

        result = retrieval.conversational_search(parsed)
        assert [c.item_id for c in result.candidates] == [a.id]
        assert result.candidates[0].rerank_score == 70
        assert result.stage1_count == 1  # only A survived the text threshold

    def test_parse_search_query_returns_parsed(self, monkeypatch):
        monkeypatch.setattr(
            retrieval.llm,
            "cached_call_flash",
            lambda *args, **kwargs: {
                "semantic_query": "blue water bottle",
                "search_type": "lost",
                "item_type": "water bottle",
                "color": "blue",
                "location": "library",
                "time_window_hours": 24,
            },
        )
        parsed = retrieval.parse_search_query("I lost a blue bottle at the library")
        assert parsed.semantic_query == "blue water bottle"
        assert parsed.search_type == "lost"
        assert parsed.color == "blue"
        assert parsed.time_window_hours == 24
