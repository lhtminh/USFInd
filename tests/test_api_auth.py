"""End-to-end tests for the FastAPI auth + me + write endpoints.

Uses FastAPI's TestClient (which maintains cookies across calls), runs against
the real Neon database (skipped otherwise), and the in-memory Qdrant client.
"""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from api.main import app
from app.core import db, vectors
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


@pytest.fixture
def client():
    # Plain TestClient (no `with` block): skips the FastAPI lifespan so we don't
    # re-run migrations + CLIP warmup for every test. The schema fixture above
    # already migrates explicitly.
    return TestClient(app)


class TestAuthCycle:
    def test_sign_in_creates_user_and_sets_cookie(self, client: TestClient):
        response = client.post("/api/auth/sign-in", json={"email": "ada@usf.edu", "name": "Ada"})
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "ada@usf.edu"
        assert body["name"] == "Ada"
        assert "usfind_session" in response.cookies

    def test_me_returns_signed_in_user(self, client: TestClient):
        client.post("/api/auth/sign-in", json={"email": "bea@usf.edu", "name": "Bea"})
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "bea@usf.edu"

    def test_me_without_cookie_returns_401(self, client: TestClient):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_sign_out_clears_session(self, client: TestClient):
        client.post("/api/auth/sign-in", json={"email": "carl@usf.edu", "name": "Carl"})
        assert client.get("/api/auth/me").status_code == 200
        client.post("/api/auth/sign-out")
        client.cookies.clear()
        assert client.get("/api/auth/me").status_code == 401

    def test_invalid_email_rejected(self, client: TestClient):
        response = client.post("/api/auth/sign-in", json={"email": "not-an-email"})
        assert response.status_code == 400

    def test_sign_in_is_idempotent_on_email(self, client: TestClient):
        first = client.post(
            "/api/auth/sign-in", json={"email": "dee@usf.edu", "name": "Dee"}
        ).json()
        second = client.post(
            "/api/auth/sign-in", json={"email": "dee@usf.edu", "name": "Deeanna"}
        ).json()
        assert first["id"] == second["id"]
        assert second["name"] == "Deeanna"


class TestProtectedEndpoints:
    def test_create_item_requires_auth(self, client: TestClient):
        response = client.post(
            "/api/items",
            data={"type": "lost", "title": "test"},
            files={"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
        assert response.status_code == 401

    def test_confirm_match_requires_auth(self, client: TestClient):
        from uuid import uuid4

        response = client.post(
            f"/api/items/{uuid4()}/confirm",
            json={"matched_item_id": str(uuid4()), "combined_score": 0.9},
        )
        assert response.status_code == 401

    def test_me_items_requires_auth(self, client: TestClient):
        assert client.get("/api/me/items").status_code == 401
        assert client.get("/api/me/matches").status_code == 401

    def test_me_items_lists_own_posts_after_sign_in(self, client: TestClient):
        client.post("/api/auth/sign-in", json={"email": "eve@usf.edu", "name": "Eve"})
        # Insert one item directly via db to avoid the multipart pipeline.
        from uuid import UUID

        user_id = UUID(client.get("/api/auth/me").json()["id"])
        db.insert_item(user_id, "lost", "My missing umbrella", None, "u", "k", "Library")
        items_resp = client.get("/api/me/items")
        assert items_resp.status_code == 200
        titles = {it["title"] for it in items_resp.json()}
        assert "My missing umbrella" in titles
