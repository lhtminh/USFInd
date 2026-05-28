"""Rolling in-process metrics: stage timings over the last 100 retrievals."""

from __future__ import annotations

import threading
from collections import deque

WINDOW_SIZE = 100

_lock = threading.Lock()
_window: deque[tuple[float, float, float, bool]] = deque(maxlen=WINDOW_SIZE)


def record(stage1_ms: float, stage2_ms: float, total_ms: float, cache_hit: bool) -> None:
    """Record one retrieval's per-stage timings and whether rerank was cached."""
    with _lock:
        _window.append((stage1_ms, stage2_ms, total_ms, cache_hit))


def snapshot() -> list[tuple[float, float, float, bool]]:
    with _lock:
        return list(_window)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(pct * len(ordered)))
    return ordered[index]


def percentiles() -> dict:
    """Return p50/p95/p99 for each stage plus the rerank-cache hit rate."""
    rows = snapshot()
    if not rows:
        return {"samples": 0}
    stage1 = [r[0] for r in rows]
    stage2 = [r[1] for r in rows]
    total = [r[2] for r in rows]
    hits = sum(1 for r in rows if r[3])
    return {
        "samples": len(rows),
        "stage1": {
            "p50": _percentile(stage1, 0.50),
            "p95": _percentile(stage1, 0.95),
            "p99": _percentile(stage1, 0.99),
        },
        "stage2": {
            "p50": _percentile(stage2, 0.50),
            "p95": _percentile(stage2, 0.95),
            "p99": _percentile(stage2, 0.99),
        },
        "total": {
            "p50": _percentile(total, 0.50),
            "p95": _percentile(total, 0.95),
            "p99": _percentile(total, 0.99),
        },
        "rerank_cache_hit_rate": hits / len(rows),
    }


def reset() -> None:
    """Clear the window (used by tests)."""
    with _lock:
        _window.clear()
