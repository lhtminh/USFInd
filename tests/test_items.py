"""Tests for app.core.items pipeline (Neon DB + in-memory Qdrant + local storage).

Skipped when no Postgres is reachable.
"""

from __future__ import annotations

from io import BytesIO

import psycopg
import pytest
from PIL import Image
from qdrant_client import QdrantClient

from app.core import db, items, storage, vectors
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


def _jpeg_bytes(color=(20, 80, 160)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (96, 96), color).save(buf, format="JPEG")
    return buf.getvalue()


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
def environment(schema, tmp_path, monkeypatch):
    with db.get_conn() as conn:
        conn.execute("TRUNCATE matches, items, users RESTART IDENTITY CASCADE")
        conn.commit()
    monkeypatch.setattr(vectors, "_client", QdrantClient(location=":memory:"))
    vectors.ensure_collections()
    monkeypatch.setattr(storage, "get_storage", lambda: storage.LocalImageStorage(tmp_path))
    yield
    monkeypatch.setattr(vectors, "_client", None)


class TestItemsPipeline:
    def test_create_item_indexes_and_marks_ready(self, tmp_path):
        user = db.upsert_user("poster@usf.edu", "Pat")
        item = items.create_item(
            user_id=user.id,
            type="found",
            title="Blue water bottle",
            description="Hydro Flask, dented lid",
            location="Library",
            uploaded_file=_jpeg_bytes(),
        )
        assert item.embedding_status == "ready"
        assert item.image_key == f"items/{user.id}/{item.id}.jpg"
        assert (tmp_path / item.image_key).exists()

        image_vec, text_vec = vectors.get_embeddings(item.id)
        assert image_vec is not None and text_vec is not None

    def test_create_item_stores_ai_description(self, tmp_path):
        user = db.upsert_user("ai@usf.edu", "Ada")
        item = items.create_item(
            user_id=user.id,
            type="found",
            title="Red umbrella",
            description="user typed",
            location=None,
            uploaded_file=_jpeg_bytes(),
            ai_description="Red compact umbrella, broken rib",
        )
        assert item.ai_description == "Red compact umbrella, broken rib"
        assert item.description == "user typed"

    def test_create_item_marks_failed_on_index_error(self, monkeypatch):
        user = db.upsert_user("fail@usf.edu", "Fay")

        def boom(*_args, **_kwargs):
            raise vectors.VectorStoreError("qdrant down")

        monkeypatch.setattr(vectors, "upsert_image_embedding", boom)

        with pytest.raises(vectors.VectorStoreError):
            items.create_item(
                user_id=user.id,
                type="lost",
                title="Lost keys",
                description=None,
                location=None,
                uploaded_file=_jpeg_bytes(),
            )

        failed = db.list_items_by_embedding_status("failed")
        assert any(it.title == "Lost keys" for it in failed)

    def test_backfill_repairs_failed_items(self):
        user = db.upsert_user("back@usf.edu", "Bea")
        item = items.create_item(
            user_id=user.id,
            type="found",
            title="Black umbrella",
            description="Compact, broken rib",
            location="MSC",
            uploaded_file=_jpeg_bytes(color=(0, 0, 0)),
        )
        # Simulate a prior failure: drop vectors and flip status.
        vectors.delete_item(item.id)
        db.update_embedding_status(item.id, "failed")
        assert vectors.get_embeddings(item.id) == (None, None)

        summary = items.backfill_failed_embeddings()
        assert summary["attempted"] == 1
        assert summary["succeeded"] == 1

        refreshed = db.get_item(item.id)
        assert refreshed is not None and refreshed.embedding_status == "ready"
        image_vec, text_vec = vectors.get_embeddings(item.id)
        assert image_vec is not None and text_vec is not None
