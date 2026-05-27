"""Two-stage retrieval: fast Qdrant vector recall, then Gemini Pro re-ranking.

Stage 1 fuses parallel image and text vector searches into a weighted candidate
list; Stage 2 (added alongside) sends the top candidates to a vision LLM for
precise re-scoring with explanations.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel

from app.core import db, vectors
from app.core.db import Item

logger = logging.getLogger(__name__)

IMAGE_WEIGHT = 0.7
TEXT_WEIGHT = 0.3
COMBINED_THRESHOLD = 0.45
RECALL_WINDOW_DAYS = 60


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
