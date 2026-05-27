"""Tests for app.core.retrieval Stage 1 recall (Neon + in-memory Qdrant)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import psycopg
import pytest
from qdrant_client import QdrantClient

from app.core import db, retrieval, vectors
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
DROP TABLE IF EXISTS matches, items, users, schema_migrations CASCADE;
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
        conn.execute("TRUNCATE matches, items, users RESTART IDENTITY CASCADE")
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
