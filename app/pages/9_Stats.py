"""Public observability dashboard: scale, latency, cache, cost, and infra."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import cache, cost_tracking, db, metrics, vectors  # noqa: E402
from app.ui_common import init_app, render_sidebar  # noqa: E402

st.set_page_config(page_title="Stats · USFind", page_icon="⚙️", layout="wide")
init_app()
render_sidebar()

st.title("USFind — engineering dashboard ⚙️")

# --- System scale ---------------------------------------------------------
st.subheader("System scale")
try:
    stats = db.get_system_stats()
except Exception:
    st.warning("System stats unavailable")
    stats = {}

cols = st.columns(4)
cols[0].metric("Users", stats.get("users", 0))
cols[1].metric(
    "Open items",
    stats.get("open_total", 0),
    delta=f"{stats.get('lost_total', 0)} lost / {stats.get('found_total', 0)} found",
)
cols[2].metric("Confirmed matches", stats.get("matches", 0))
cols[3].metric(
    "Match success rate",
    f"{(stats.get('match_success_rate', 0.0) or 0.0) * 100:.0f}%",
    help="Share of lost items that have been matched.",
)

st.divider()

# --- Pipeline latency -----------------------------------------------------
st.subheader("AI pipeline latency (rolling window of last 100 retrievals)")
perf = metrics.percentiles()
if perf.get("samples", 0) == 0:
    st.info("No retrievals recorded yet — run the Matches or Search page to populate.")
else:
    for stage_key, label in [
        ("stage1", "Stage 1 (Qdrant recall)"),
        ("stage2", "Stage 2 (Gemini rerank)"),
        ("total", "End-to-end"),
    ]:
        s = perf[stage_key]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{label} p50", f"{s['p50']:.0f} ms")
        c2.metric(f"{label} p95", f"{s['p95']:.0f} ms")
        c3.metric(f"{label} p99", f"{s['p99']:.0f} ms")
    st.caption(f"Samples in window: {perf['samples']}")

st.divider()

# --- Cache performance ----------------------------------------------------
st.subheader("Cache performance")
cstats = cache.cache_stats()


def _rate(hits: int, misses: int) -> str:
    total = hits + misses
    return f"{(hits / total * 100):.0f}%" if total else "—"


c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Image emb cache",
    _rate(cstats["image_hits"], cstats["image_misses"]),
    delta=f"{cstats['image_hits']}/{cstats['image_hits'] + cstats['image_misses']}",
)
c2.metric(
    "Text emb cache",
    _rate(cstats["text_hits"], cstats["text_misses"]),
    delta=f"{cstats['text_hits']}/{cstats['text_hits'] + cstats['text_misses']}",
)
c3.metric(
    "LLM cache",
    _rate(cstats["llm_hits"], cstats["llm_misses"]),
    delta=f"{cstats['llm_hits']}/{cstats['llm_hits'] + cstats['llm_misses']}",
)
c4.metric(
    "Rerank cache",
    _rate(cstats["rerank_hits"], cstats["rerank_misses"]),
    delta=f"{cstats['rerank_hits']}/{cstats['rerank_hits'] + cstats['rerank_misses']}",
)

st.divider()

# --- Cost tracking --------------------------------------------------------
st.subheader("Gemini cost")
c1, c2, c3 = st.columns(3)
c1.metric("Today", f"${cost_tracking.get_daily_cost():.4f}")
c2.metric("Last 30 days", f"${cost_tracking.get_monthly_cost():.4f}")
endpoint_costs = cost_tracking.get_cost_by_endpoint(days=7)
c3.metric("Endpoints (7d)", len(endpoint_costs))
if endpoint_costs:
    st.write({endpoint: f"${cost:.4f}" for endpoint, cost in endpoint_costs.items()})

st.divider()

# --- Vector DB ------------------------------------------------------------
st.subheader("Vector database")
try:
    vstats = vectors.collection_stats()
    cols = st.columns(2)
    for col, (name, info) in zip(cols, vstats.items(), strict=False):
        col.metric(name, info.get("points_count", 0), delta=info.get("status", ""))
except Exception:
    st.info("Qdrant unavailable.")

st.divider()

# --- Architecture ---------------------------------------------------------
st.subheader("Architecture")
st.code(
    """
Streamlit (UI)  ──→  Postgres (relational data, on Neon)
              ├──→  Qdrant (vector search, HNSW)
              ├──→  Redis (3-layer cache: emb img/txt + LLM + rerank)
              ├──→  Gemini Flash + Pro (vision + rerank)
              └──→  Cloudflare R2 (image storage)
""",
    language="text",
)
st.caption("Pipeline: Qdrant HNSW recall (top 50) → Gemini 2.5 Pro re-ranking (top 10)")
