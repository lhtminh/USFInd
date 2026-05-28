"""Aggregations over the llm_usage table for the stats dashboard."""

from __future__ import annotations

import logging

from app.core import db

logger = logging.getLogger(__name__)


def _sum_cost_since(days: int) -> float:
    """Sum llm_usage.cost_usd over the last ``days`` days. 0.0 on failure."""
    try:
        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(cost_usd), 0.0)::float
                FROM llm_usage
                WHERE called_at >= NOW() - (INTERVAL '1 day' * %s)
                """,
                (days,),
            )
            row = cur.fetchone()
            return float(row[0]) if row else 0.0
    except Exception as exc:
        logger.warning("cost_tracking query failed: %s", exc)
        return 0.0


def get_daily_cost() -> float:
    """Total Gemini USD cost over the last 24h."""
    return _sum_cost_since(1)


def get_monthly_cost() -> float:
    """Total Gemini USD cost over the last 30 days."""
    return _sum_cost_since(30)


def get_cost_by_endpoint(days: int = 7) -> dict[str, float]:
    """Per-endpoint USD cost totals over the last ``days`` days."""
    try:
        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT endpoint, COALESCE(SUM(cost_usd), 0.0)::float
                FROM llm_usage
                WHERE called_at >= NOW() - (INTERVAL '1 day' * %s)
                GROUP BY endpoint
                ORDER BY 2 DESC
                """,
                (days,),
            )
            return {row[0]: float(row[1]) for row in cur.fetchall()}
    except Exception as exc:
        logger.warning("cost_tracking endpoint query failed: %s", exc)
        return {}
