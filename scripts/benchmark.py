"""CLI: benchmark the 2-stage retrieval pipeline and write a markdown report.

Usage:
    python -m scripts.benchmark --num-queries 50 [--flush-cache]

Run twice (once with ``--flush-cache``, once without) to compare cold vs warm
cache. The report lands at ``docs/BENCHMARK.md``; subsequent runs overwrite it.
"""

from __future__ import annotations

import argparse
import logging
import random
from datetime import UTC, datetime
from pathlib import Path

from app.core import cache, db, retrieval, vectors
from app.core.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger("scripts.benchmark")


def _percentiles(values: list[float]) -> dict[float, float]:
    if not values:
        return {0.50: 0.0, 0.95: 0.0, 0.99: 0.0}
    ordered = sorted(values)
    n = len(ordered)
    return {p: ordered[min(n - 1, int(p * n))] for p in (0.50, 0.95, 0.99)}


def _delta_rate(cache_start: dict, cache_end: dict, key: str) -> tuple[int, int, str]:
    delta_hits = cache_end[f"{key}_hits"] - cache_start[f"{key}_hits"]
    delta_misses = cache_end[f"{key}_misses"] - cache_start[f"{key}_misses"]
    total = delta_hits + delta_misses
    rate = f"{(delta_hits / total * 100):.0f}%" if total else "—"
    return delta_hits, delta_misses, rate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-queries", type=int, default=50)
    parser.add_argument("--flush-cache", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)

    if args.flush_cache:
        try:
            cache.get_client().flushdb()
            print("Redis flushed (cold-cache run).")
        except Exception as exc:
            logger.warning("Could not flush Redis: %s", exc)

    pool = db.list_items(type=None, status="open", limit=500, offset=0)
    if len(pool) < 2:
        print("Not enough items in the DB to benchmark. Run scripts.seed_data first.")
        return

    rng = random.Random(0)
    queries = rng.sample(pool, min(args.num_queries, len(pool)))

    stage1_ms: list[float] = []
    stage2_ms: list[float] = []
    total_ms: list[float] = []
    rerank_hits = 0
    errors = 0

    cache_start = cache.cache_stats()

    for query in queries:
        try:
            result = retrieval.full_retrieval(query.id)
        except Exception as exc:
            logger.warning("Retrieval failed for %s: %s", query.id, exc)
            errors += 1
            continue
        stage1_ms.append(result.stage1_ms)
        stage2_ms.append(result.stage2_ms)
        total_ms.append(result.total_ms)
        if result.cache_hit:
            rerank_hits += 1

    cache_end = cache.cache_stats()
    p1 = _percentiles(stage1_ms)
    p2 = _percentiles(stage2_ms)
    pt = _percentiles(total_ms)
    vstats = vectors.collection_stats()

    lines: list[str] = []
    lines.append("# USFind benchmark report\n\n")
    lines.append(f"_Generated: {datetime.now(UTC).isoformat()}_\n\n")
    lines.append(
        f"Parameters: `--num-queries {args.num_queries}`, "
        f"`flush-cache={args.flush_cache}` · queries: {len(stage1_ms)} (errors: {errors})\n\n"
    )
    lines.append("## Latency (ms)\n\n")
    lines.append("| Stage | p50 | p95 | p99 |\n|---|---:|---:|---:|\n")
    lines.append(
        f"| Stage 1 (Qdrant recall) | {p1[0.50]:.0f} | {p1[0.95]:.0f} | {p1[0.99]:.0f} |\n"
    )
    lines.append(
        f"| Stage 2 (Gemini rerank) | {p2[0.50]:.0f} | {p2[0.95]:.0f} | {p2[0.99]:.0f} |\n"
    )
    lines.append(f"| End-to-end | {pt[0.50]:.0f} | {pt[0.95]:.0f} | {pt[0.99]:.0f} |\n\n")
    lines.append(f"Rerank-cache hits during run: **{rerank_hits} / {len(stage1_ms)}**\n\n")
    lines.append("## Cache deltas (this run)\n\n")
    lines.append("| Layer | Hits | Misses | Hit rate |\n|---|---:|---:|---:|\n")
    for key in ("image", "text", "llm", "rerank"):
        hits, misses, rate = _delta_rate(cache_start, cache_end, key)
        lines.append(f"| {key} | {hits} | {misses} | {rate} |\n")
    lines.append("\n## Qdrant collections\n\n")
    for name, info in vstats.items():
        lines.append(
            f"- **{name}**: {info.get('points_count', 0)} points, "
            f"status `{info.get('status', '')}`\n"
        )

    out = Path("docs/BENCHMARK.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote benchmark report → {out}")


if __name__ == "__main__":
    main()
