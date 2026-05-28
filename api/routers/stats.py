"""Public stats endpoint feeding the dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import StatsOut
from app.core import cache, cost_tracking, db, metrics, vectors

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats() -> StatsOut:
    try:
        system = db.get_system_stats()
    except Exception:
        system = {}
    perf = metrics.percentiles()
    try:
        qdrant_stats = vectors.collection_stats()
    except Exception:
        qdrant_stats = {}
    return StatsOut(
        users=int(system.get("users", 0) or 0),
        open_total=int(system.get("open_total", 0) or 0),
        lost_total=int(system.get("lost_total", 0) or 0),
        found_total=int(system.get("found_total", 0) or 0),
        matched_total=int(system.get("matched_total", 0) or 0),
        matches=int(system.get("matches", 0) or 0),
        match_success_rate=float(system.get("match_success_rate", 0.0) or 0.0),
        cache=cache.cache_stats(),
        latency_samples=int(perf.get("samples", 0) or 0),
        latency={
            "stage1": perf.get("stage1", {}),
            "stage2": perf.get("stage2", {}),
            "total": perf.get("total", {}),
        },
        cost={
            "today": cost_tracking.get_daily_cost(),
            "last30": cost_tracking.get_monthly_cost(),
            "by_endpoint": cost_tracking.get_cost_by_endpoint(days=7),
        },
        qdrant=qdrant_stats,
    )
