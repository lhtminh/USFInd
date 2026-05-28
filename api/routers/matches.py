"""Run the 2-stage retrieval pipeline for a query item."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.image_urls import public_image_url
from api.schemas import CandidateOut, ItemOut, MatchesResult
from app.core import db, retrieval

router = APIRouter(prefix="/api/items", tags=["matches"])


def _base_url(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


@router.post("/{item_id}/matches", response_model=MatchesResult)
def matches(item_id: UUID, request: Request, final_k: int = 10) -> MatchesResult:
    query = db.get_item(item_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        result = retrieval.full_retrieval(item_id, final_k=final_k)
    except retrieval.RetrievalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    base = _base_url(request)
    return MatchesResult(
        query=ItemOut.from_item(query, image_url=public_image_url(query, base)),
        candidates=[
            CandidateOut(
                item=ItemOut.from_item(
                    candidate.item, image_url=public_image_url(candidate.item, base)
                ),
                combined_score=candidate.combined_score,
                image_score=candidate.image_score,
                text_score=candidate.text_score,
                rerank_score=candidate.rerank_score,
                explanation=candidate.explanation,
                stage1_rank=candidate.stage1_rank,
            )
            for candidate in result.candidates
        ],
        stage1_count=result.stage1_count,
        stage1_ms=result.stage1_ms,
        stage2_ms=result.stage2_ms,
        total_ms=result.total_ms,
        cache_hit=result.cache_hit,
    )
