"""Two-stage retrieval: fast Qdrant vector recall, then Gemini Pro re-ranking.

Stage 1 fuses parallel image and text vector searches into a weighted candidate
list; Stage 2 (added alongside) sends the top candidates to a vision LLM for
precise re-scoring with explanations.
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from PIL import Image
from pydantic import BaseModel

from app.core import cache, db, embeddings, llm, metrics, storage, vectors
from app.core.db import Item

logger = logging.getLogger(__name__)

IMAGE_WEIGHT = 0.7
TEXT_WEIGHT = 0.3
COMBINED_THRESHOLD = 0.45
RECALL_WINDOW_DAYS = 60

RERANK_INPUT_CAP = 20
RERANK_THRESHOLD = 40
SEARCH_RECALL_K = 30
SEARCH_TEXT_THRESHOLD = 0.30
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PARSE_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "item_type": {"type": "string"},
        "color": {"type": "string"},
        "location": {"type": "string"},
        "time_window_hours": {"type": "integer"},
        "search_type": {"type": "string", "enum": ["lost", "found", "either"]},
        "semantic_query": {"type": "string"},
    },
    "required": ["semantic_query", "search_type"],
}

_RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_index": {"type": "integer"},
                    "rerank_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "explanation": {"type": "string"},
                },
                "required": ["candidate_index", "rerank_score", "explanation"],
            },
        }
    },
    "required": ["rankings"],
}


class RetrievalError(Exception):
    """Raised when retrieval cannot proceed (missing item or embeddings)."""


class Candidate(BaseModel):
    item_id: UUID
    combined_score: float
    image_score: float
    text_score: float
    item: Item
    stage1_rank: int = 0
    rerank_score: float | None = None
    explanation: str | None = None


class RetrievalResult(BaseModel):
    candidates: list[Candidate]
    stage1_count: int
    stage1_ms: float
    stage2_ms: float
    total_ms: float
    cache_hit: bool = False


class ParsedSearch(BaseModel):
    semantic_query: str
    search_type: Literal["lost", "found", "either"] = "either"
    item_type: str | None = None
    color: str | None = None
    location: str | None = None
    time_window_hours: int | None = None


def stage1_recall(query_item_id: UUID, top_k: int = 50) -> list[Candidate]:
    """Recall up to ``top_k`` opposite-type candidates by fused vector similarity.

    Raises:
        RetrievalError: if the query item or its embeddings are missing.
    """
    start = time.perf_counter()
    query = db.get_item(query_item_id)
    if query is None:
        raise RetrievalError(f"Query item {query_item_id} not found")

    image_vec, text_vec = vectors.get_embeddings(query_item_id)
    if image_vec is None or text_vec is None:
        raise RetrievalError(f"Query item {query_item_id} is missing embeddings")

    opposite_type = "found" if query.type == "lost" else "lost"
    created_after = int((datetime.now(UTC) - timedelta(days=RECALL_WINDOW_DAYS)).timestamp())
    qfilter = vectors.build_filter(
        item_type=opposite_type,
        status="open",
        created_after_ts=created_after,
        exclude_item_id=query_item_id,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        image_future = executor.submit(vectors.search_image, image_vec, qfilter, top_k)
        text_future = executor.submit(vectors.search_text, text_vec, qfilter, top_k)
        image_hits = image_future.result()
        text_hits = text_future.result()

    image_scores = {UUID(str(hit.id)): hit.score for hit in image_hits}
    text_scores = {UUID(str(hit.id)): hit.score for hit in text_hits}

    fused: list[tuple[UUID, float, float, float]] = []
    for item_id in set(image_scores) | set(text_scores):
        image_score = image_scores.get(item_id, 0.0)
        text_score = text_scores.get(item_id, 0.0)
        combined = IMAGE_WEIGHT * image_score + TEXT_WEIGHT * text_score
        if combined >= COMBINED_THRESHOLD:
            fused.append((item_id, combined, image_score, text_score))

    fused.sort(key=lambda row: row[1], reverse=True)
    fused = fused[:top_k]

    items_by_id = db.list_items_by_ids([row[0] for row in fused])
    candidates: list[Candidate] = []
    for rank, (item_id, combined, image_score, text_score) in enumerate(fused, start=1):
        item = items_by_id.get(item_id)
        if item is None:
            continue
        candidates.append(
            Candidate(
                item_id=item_id,
                combined_score=combined,
                image_score=image_score,
                text_score=text_score,
                item=item,
                stage1_rank=rank,
            )
        )

    logger.info(
        "Stage 1 recall for %s: %d candidates in %.1fms",
        query_item_id,
        len(candidates),
        (time.perf_counter() - start) * 1000,
    )
    return candidates


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _item_metadata(item: Item) -> str:
    return (
        f"type={item.type}; title={item.title}; "
        f"description={item.description or ''}; location={item.location or ''}"
    )


def _load_image(item: Item) -> Image.Image | None:
    """Best-effort load of an item's image for the LLM; None if unavailable."""
    try:
        data = storage.get_storage().download(item.image_key)
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        logger.warning("Could not load image for item %s during rerank", item.id)
        return None


def _build_rerank_parts(query_item: Item, candidates: list[Candidate]) -> list:
    parts: list = ["QUERY ITEM:\n" + _item_metadata(query_item)]
    query_image = _load_image(query_item)
    if query_image is not None:
        parts.append(query_image)
    parts.append(f"CANDIDATES (numbered 1-{len(candidates)}):")
    for index, candidate in enumerate(candidates, start=1):
        parts.append(f"[{index}] " + _item_metadata(candidate.item))
        candidate_image = _load_image(candidate.item)
        if candidate_image is not None:
            parts.append(candidate_image)
    parts.append("Rank each candidate by likelihood of being the same physical item.")
    return parts


def stage2_rerank(
    query_item: Item, candidates: list[Candidate], top_k: int = 10
) -> list[Candidate]:
    """Re-score the top stage-1 candidates with Gemini Pro and keep the best.

    Caps input at 20 candidates, attaches a 0-100 rerank score and explanation,
    drops anything below 40, and returns the top ``top_k`` by score. Tolerates a
    query item with no loadable image (e.g. conversational search).
    """
    if not candidates:
        return []

    capped = candidates[:RERANK_INPUT_CAP]
    system_instruction = _load_prompt("rerank.txt")
    parts = _build_rerank_parts(query_item, capped)
    response = llm.cached_call_pro(
        parts,
        system_instruction=system_instruction,
        response_schema=_RERANK_SCHEMA,
        endpoint="rerank",
    )

    by_index = {r["candidate_index"]: r for r in response.get("rankings", [])}
    reranked: list[Candidate] = []
    for index, candidate in enumerate(capped, start=1):
        ranking = by_index.get(index)
        if ranking is None:
            continue
        candidate.rerank_score = float(ranking["rerank_score"])
        candidate.explanation = ranking.get("explanation")
        if candidate.rerank_score >= RERANK_THRESHOLD:
            reranked.append(candidate)

    reranked.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
    return reranked[:top_k]


def _rerank_cache_key(query_item: Item, candidates: list[Candidate]) -> str:
    """Content-aware key: invalidates when the query updates or the candidate set changes."""
    sorted_ids = sorted(str(c.item_id) for c in candidates)
    digest = hashlib.sha256("".join(sorted_ids).encode("utf-8")).hexdigest()
    updated_ts = int(query_item.updated_at.timestamp())
    return f"rerank:v1:{query_item.id}:{updated_ts}:{digest}"


def full_retrieval(query_item_id: UUID, final_k: int = 10) -> RetrievalResult:
    """Run both retrieval stages and return ranked matches with timings.

    Stage 2 is cached (24h) under a key derived from the query's updated_at and
    the sorted candidate ids, so edits to the query naturally invalidate it.
    """
    overall_start = time.perf_counter()

    stage1_start = time.perf_counter()
    candidates = stage1_recall(query_item_id)
    stage1_ms = (time.perf_counter() - stage1_start) * 1000

    query_item = db.get_item(query_item_id)
    if query_item is None:
        raise RetrievalError(f"Query item {query_item_id} not found")

    cache_key = _rerank_cache_key(query_item, candidates)
    stage2_start = time.perf_counter()
    cached = cache.get_cached_rerank(cache_key)
    if cached is not None:
        reranked = [Candidate.model_validate(entry) for entry in cached]
        cache_hit = True
    else:
        reranked = stage2_rerank(query_item, candidates, top_k=final_k)
        cache.set_cached_rerank(cache_key, [c.model_dump(mode="json") for c in reranked])
        cache_hit = False
    stage2_ms = (time.perf_counter() - stage2_start) * 1000

    total_ms = (time.perf_counter() - overall_start) * 1000
    metrics.record(stage1_ms, stage2_ms, total_ms, cache_hit)
    return RetrievalResult(
        candidates=reranked,
        stage1_count=len(candidates),
        stage1_ms=stage1_ms,
        stage2_ms=stage2_ms,
        total_ms=total_ms,
        cache_hit=cache_hit,
    )


def parse_search_query(query: str) -> ParsedSearch:
    """Use Gemini Flash to parse a free-text search into structured filters."""
    system_instruction = _load_prompt("parse_search.txt")
    response = llm.cached_call_flash(
        parts=[query],
        system_instruction=system_instruction,
        response_schema=PARSE_SEARCH_SCHEMA,
        endpoint="parse_search",
    )
    # The schema guarantees semantic_query + search_type; fall back defensively.
    response.setdefault("semantic_query", query)
    response.setdefault("search_type", "either")
    return ParsedSearch.model_validate(response)


def _virtual_query_item(parsed: ParsedSearch) -> Item:
    """Construct a placeholder Item for stage 2 rerank in conversational search."""
    now = datetime.now(UTC)
    inferred_type = "lost" if parsed.search_type == "found" else "found"
    return Item(
        id=uuid4(),
        user_id=uuid4(),
        type=inferred_type,
        title=parsed.semantic_query,
        description=None,
        ai_description=None,
        image_url="",
        image_key="",
        location=parsed.location,
        status="open",
        embedding_status="ready",
        created_at=now,
        updated_at=now,
    )


def conversational_search(
    parsed: ParsedSearch, top_k: int = SEARCH_RECALL_K, final_k: int = 10
) -> RetrievalResult:
    """Text-only recall (CLIP embedding of the parsed query) + Gemini Pro rerank."""
    overall_start = time.perf_counter()

    stage1_start = time.perf_counter()
    text_vector = embeddings.embed_text(parsed.semantic_query)

    type_filter: str | None
    if parsed.search_type == "lost":
        type_filter = "found"
    elif parsed.search_type == "found":
        type_filter = "lost"
    else:
        type_filter = None

    created_after: int | None = None
    if parsed.time_window_hours and parsed.time_window_hours > 0:
        created_after = int(
            (datetime.now(UTC) - timedelta(hours=parsed.time_window_hours)).timestamp()
        )

    qfilter = vectors.build_filter(
        item_type=type_filter, status="open", created_after_ts=created_after
    )
    hits = vectors.search_text(text_vector, qfilter, top_k)
    stage1_ms = (time.perf_counter() - stage1_start) * 1000

    item_ids = [UUID(str(hit.id)) for hit in hits]
    items_by_id = db.list_items_by_ids(item_ids)
    candidates: list[Candidate] = []
    for rank, hit in enumerate(hits, start=1):
        score = float(hit.score)
        if score < SEARCH_TEXT_THRESHOLD:
            continue
        item_id = UUID(str(hit.id))
        item = items_by_id.get(item_id)
        if item is None:
            continue
        candidates.append(
            Candidate(
                item_id=item_id,
                combined_score=score,
                image_score=0.0,
                text_score=score,
                item=item,
                stage1_rank=rank,
            )
        )

    stage2_start = time.perf_counter()
    reranked = stage2_rerank(_virtual_query_item(parsed), candidates, top_k=final_k)
    stage2_ms = (time.perf_counter() - stage2_start) * 1000

    return RetrievalResult(
        candidates=reranked,
        stage1_count=len(candidates),
        stage1_ms=stage1_ms,
        stage2_ms=stage2_ms,
        total_ms=(time.perf_counter() - overall_start) * 1000,
        cache_hit=False,
    )
