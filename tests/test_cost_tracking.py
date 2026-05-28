"""Tests for llm_usage logging (via llm._call) and cost_tracking aggregations."""

from __future__ import annotations

import psycopg
import pytest

from app.core import cost_tracking, db, llm
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
def clean(schema):
    with db.get_conn() as conn:
        conn.execute("TRUNCATE matches, items, users, llm_usage RESTART IDENTITY CASCADE")
        conn.commit()
    yield


class _Usage:
    def __init__(self, prompt: int, output: int) -> None:
        self.prompt_token_count = prompt
        self.candidates_token_count = output


class _Resp:
    def __init__(self, text: str, prompt: int = 100, output: int = 50) -> None:
        self.text = text
        self.usage_metadata = _Usage(prompt, output)


class TestLlmUsageLogging:
    def test_call_flash_writes_a_usage_row(self, monkeypatch):
        class FakeModel:
            def __init__(self, *a, **k):
                pass

            def generate_content(self, *a, **k):
                return _Resp("hello")

        monkeypatch.setattr(llm.genai, "GenerativeModel", FakeModel)
        monkeypatch.setattr(llm.time, "sleep", lambda *_: None)

        llm.call_flash(["hi"], endpoint="auto_describe")

        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT model, endpoint, cache_hit, input_tokens FROM llm_usage")
            rows = cur.fetchall()

        assert len(rows) == 1
        assert rows[0] == (llm.FLASH_MODEL, "auto_describe", False, 100)

    def test_cached_call_records_hit_with_zero_tokens(self, monkeypatch):
        from fakeredis import FakeRedis

        from app.core import cache

        monkeypatch.setattr(cache, "_client", FakeRedis())

        class FakeModel:
            def __init__(self, *a, **k):
                pass

            def generate_content(self, *a, **k):
                return _Resp("cached")

        monkeypatch.setattr(llm.genai, "GenerativeModel", FakeModel)
        monkeypatch.setattr(llm.time, "sleep", lambda *_: None)

        llm.cached_call_flash(["q"], endpoint="parse_search")  # miss -> 1 row
        llm.cached_call_flash(["q"], endpoint="parse_search")  # hit  -> 1 row

        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT cache_hit, input_tokens, output_tokens FROM llm_usage ORDER BY id")
            rows = cur.fetchall()

        assert len(rows) == 2
        assert rows[0][0] is False and rows[0][1] > 0
        assert rows[1] == (True, 0, 0)


class TestCostTracking:
    def _seed(self, endpoint: str, cost: float, days_ago: int = 0) -> None:
        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_usage
                  (called_at, model, input_tokens, output_tokens, cost_usd,
                   latency_ms, cache_hit, endpoint)
                VALUES (NOW() - (INTERVAL '1 day' * %s), %s, 0, 0, %s, 0, FALSE, %s)
                """,
                (days_ago, llm.FLASH_MODEL, cost, endpoint),
            )
            conn.commit()

    def test_daily_and_monthly_costs(self):
        self._seed("auto_describe", 0.10, days_ago=0)
        self._seed("rerank", 0.20, days_ago=0)
        self._seed("rerank", 1.00, days_ago=15)
        self._seed("rerank", 9.99, days_ago=45)  # outside the 30-day window

        assert cost_tracking.get_daily_cost() == pytest.approx(0.30, abs=1e-4)
        assert cost_tracking.get_monthly_cost() == pytest.approx(1.30, abs=1e-4)

    def test_cost_by_endpoint(self):
        self._seed("auto_describe", 0.05, days_ago=1)
        self._seed("parse_search", 0.20, days_ago=2)
        self._seed("rerank", 1.00, days_ago=3)
        breakdown = cost_tracking.get_cost_by_endpoint(days=7)
        assert breakdown == {
            "rerank": pytest.approx(1.00, abs=1e-4),
            "parse_search": pytest.approx(0.20, abs=1e-4),
            "auto_describe": pytest.approx(0.05, abs=1e-4),
        }
