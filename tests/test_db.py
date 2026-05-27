"""Tests for app.core.db against a real Postgres reachable via DATABASE_URL.

Skipped automatically when no database is reachable, so the rest of the suite
still runs offline.
"""

from __future__ import annotations

import psycopg
import pytest

from app.core import db
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


@pytest.fixture(scope="class")
def schema():
    """Create a clean schema for the test class, drop it on teardown."""
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
def clean_rows(schema):
    """Truncate mutable tables before each test for isolation."""
    with db.get_conn() as conn:
        conn.execute("TRUNCATE matches, items, users RESTART IDENTITY CASCADE")
        conn.commit()
    yield


class TestDb:
    def test_run_migrations_idempotent(self):
        # schema fixture already applied 001; a second run applies nothing.
        assert db.run_migrations() == []

    def test_upsert_user_inserts_then_updates(self):
        u1 = db.upsert_user("a@usf.edu", "Alice")
        assert u1.email == "a@usf.edu"
        assert u1.name == "Alice"
        u2 = db.upsert_user("a@usf.edu", "Alicia")
        assert u2.id == u1.id
        assert u2.name == "Alicia"

    def test_upsert_user_keeps_name_when_null_on_conflict(self):
        u1 = db.upsert_user("b@usf.edu", "Bob")
        u2 = db.upsert_user("b@usf.edu", None)
        assert u2.id == u1.id
        assert u2.name == "Bob"

    def test_insert_and_get_item_includes_poster_name(self):
        user = db.upsert_user("c@usf.edu", "Carol")
        item = db.insert_item(
            user_id=user.id,
            type="found",
            title="Black backpack",
            description="Nike, red logo",
            image_url="https://img/x.jpg",
            image_key="items/c/x.jpg",
            location="Library",
        )
        assert item.status == "open"
        assert item.embedding_status == "pending"
        fetched = db.get_item(item.id)
        assert fetched is not None
        assert fetched.title == "Black backpack"
        assert fetched.poster_name == "Carol"

    def test_get_item_missing_returns_none(self):
        from uuid import uuid4

        assert db.get_item(uuid4()) is None

    def test_insert_item_with_explicit_id(self):
        from uuid import uuid4

        user = db.upsert_user("j@usf.edu", "Jo")
        item_id = uuid4()
        item = db.insert_item(user.id, "found", "t", None, "u", "k", None, item_id=item_id)
        assert item.id == item_id

    def test_list_items_by_embedding_status(self):
        user = db.upsert_user("emb@usf.edu", "Em")
        ready = db.insert_item(user.id, "lost", "ready-item", None, "u", "k", None)
        db.update_embedding_status(ready.id, "ready")
        db.insert_item(user.id, "lost", "pending-item", None, "u", "k", None)
        titles = {it.title for it in db.list_items_by_embedding_status("ready")}
        assert titles == {"ready-item"}

    def test_list_items_filters_and_pagination(self):
        user = db.upsert_user("d@usf.edu", "Dan")
        for i in range(3):
            db.insert_item(user.id, "lost", f"lost-{i}", None, "u", "k", None)
        for i in range(2):
            db.insert_item(user.id, "found", f"found-{i}", None, "u", "k", None)

        lost = db.list_items(type="lost", status="open")
        assert {it.title for it in lost} == {"lost-0", "lost-1", "lost-2"}
        found = db.list_items(type="found", status="open")
        assert len(found) == 2
        all_open = db.list_items(type=None, status="open")
        assert len(all_open) == 5

        page1 = db.list_items(type="lost", limit=2, offset=0)
        page2 = db.list_items(type="lost", limit=2, offset=2)
        assert len(page1) == 2 and len(page2) == 1

    def test_update_statuses(self):
        user = db.upsert_user("e@usf.edu", "Eve")
        item = db.insert_item(user.id, "lost", "keys", None, "u", "k", None)
        db.update_item_status(item.id, "matched")
        db.update_embedding_status(item.id, "ready")
        refreshed = db.get_item(item.id)
        assert refreshed is not None
        assert refreshed.status == "matched"
        assert refreshed.embedding_status == "ready"

    def test_updated_at_trigger_advances(self):
        user = db.upsert_user("f@usf.edu", "Finn")
        item = db.insert_item(user.id, "lost", "wallet", None, "u", "k", None)
        db.update_item_status(item.id, "closed")
        refreshed = db.get_item(item.id)
        assert refreshed is not None
        assert refreshed.updated_at >= item.updated_at

    def test_list_user_items(self):
        u1 = db.upsert_user("g@usf.edu", "Gabe")
        u2 = db.upsert_user("h@usf.edu", "Hana")
        db.insert_item(u1.id, "lost", "u1-a", None, "u", "k", None)
        db.insert_item(u1.id, "found", "u1-b", None, "u", "k", None)
        db.insert_item(u2.id, "lost", "u2-a", None, "u", "k", None)
        assert {it.title for it in db.list_user_items(u1.id)} == {"u1-a", "u1-b"}
        assert {it.title for it in db.list_user_items(u2.id)} == {"u2-a"}

    def test_insert_match(self):
        user = db.upsert_user("i@usf.edu", "Ivy")
        a = db.insert_item(user.id, "lost", "phone", None, "u", "k", None)
        b = db.insert_item(user.id, "found", "phone2", None, "u", "k", None)
        match = db.insert_match(a.id, b.id, user.id, combined_score=0.91, rerank_score=88.0)
        assert match.item_a_id == a.id
        assert match.item_b_id == b.id
        assert match.combined_score == pytest.approx(0.91, rel=1e-5)
        assert match.rerank_score == pytest.approx(88.0, rel=1e-5)
