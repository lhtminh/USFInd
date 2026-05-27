"""Smoke tests for the Streamlit entry script via streamlit.testing.

Runs the landing page in-process and asserts it renders without raising. Skipped
when no Postgres is reachable (startup applies migrations).
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from app.core.config import get_settings

_APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


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


def test_landing_runs_without_exception():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_APP)).run(timeout=60)
    assert not at.exception


def test_landing_prompts_signin_when_logged_out():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_APP)).run(timeout=60)
    assert not at.exception
    assert len(at.info) >= 1  # sign-in prompt shown to logged-out visitors
