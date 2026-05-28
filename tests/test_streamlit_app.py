"""Smoke tests for the Streamlit entry script via streamlit.testing.

Runs the landing page in-process and asserts it renders without raising. Skipped
when no Postgres is reachable (startup applies migrations).
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from app.core.config import get_settings

_APP_DIR = Path(__file__).resolve().parents[1] / "app"
_APP = _APP_DIR / "streamlit_app.py"
_PAGES = _APP_DIR / "pages"


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


def test_browse_page_runs():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_PAGES / "2_Browse.py")).run(timeout=60)
    assert not at.exception


def test_item_detail_without_id_runs():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_PAGES / "3_Item_Detail.py")).run(timeout=60)
    assert not at.exception


def test_post_page_requires_login_when_logged_out():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_PAGES / "1_Post_Item.py")).run(timeout=60)
    assert not at.exception  # require_login halts via st.stop, not an exception


def test_post_page_renders_form_when_logged_in():
    from uuid import uuid4

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_PAGES / "1_Post_Item.py"))
    at.session_state["user"] = {"id": str(uuid4()), "email": "x@usf.edu", "name": "X"}
    at.run(timeout=60)
    assert not at.exception


def test_matches_page_without_id_runs():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_PAGES / "4_Matches.py")).run(timeout=60)
    assert not at.exception
