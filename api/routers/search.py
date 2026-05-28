"""Conversational search: parse free text then run text-only recall + rerank."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.image_urls import public_image_url
from api.schemas import CandidateOut, ItemOut, ParsedSearchOut, SearchResult
from app.core import retrieval

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    final_k: int = 10


def _base_url(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


@router.post("", response_model=SearchResult)
def search(payload: SearchRequest, request: Request) -> SearchResult:
    parsed = retrieval.parse_search_query(payload.query)
    result = retrieval.conversational_search(parsed, final_k=payload.final_k)
    base = _base_url(request)
    return SearchResult(
        parsed=ParsedSearchOut(
            semantic_query=parsed.semantic_query,
            search_type=parsed.search_type,
            item_type=parsed.item_type,
            color=parsed.color,
            location=parsed.location,
            time_window_hours=parsed.time_window_hours,
        ),
        candidates=[
            CandidateOut(
                item=ItemOut.from_item(c.item, image_url=public_image_url(c.item, base)),
                combined_score=c.combined_score,
                image_score=c.image_score,
                text_score=c.text_score,
                rerank_score=c.rerank_score,
                explanation=c.explanation,
                stage1_rank=c.stage1_rank,
            )
            for c in result.candidates
        ],
        stage1_count=result.stage1_count,
        stage1_ms=result.stage1_ms,
        stage2_ms=result.stage2_ms,
        total_ms=result.total_ms,
    )
