"""API response shapes — decoupled from db models so the wire format is stable."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.core.db import Item


class ItemOut(BaseModel):
    id: UUID
    type: str
    status: str
    title: str
    description: str | None
    ai_description: str | None
    location: str | None
    image_url: str
    poster_name: str | None
    posted_at: datetime
    embedding_status: str

    @classmethod
    def from_item(cls, item: Item, *, image_url: str) -> ItemOut:
        return cls(
            id=item.id,
            type=item.type,
            status=item.status,
            title=item.title,
            description=item.description,
            ai_description=item.ai_description,
            location=item.location,
            image_url=image_url,
            poster_name=item.poster_name,
            posted_at=item.created_at,
            embedding_status=item.embedding_status,
        )


class CandidateOut(BaseModel):
    item: ItemOut
    combined_score: float
    image_score: float
    text_score: float
    rerank_score: float | None = None
    explanation: str | None = None
    stage1_rank: int


class MatchesResult(BaseModel):
    query: ItemOut
    candidates: list[CandidateOut]
    stage1_count: int
    stage1_ms: float
    stage2_ms: float
    total_ms: float
    cache_hit: bool


class ParsedSearchOut(BaseModel):
    semantic_query: str
    search_type: Literal["lost", "found", "either"]
    item_type: str | None
    color: str | None
    location: str | None
    time_window_hours: int | None


class SearchResult(BaseModel):
    parsed: ParsedSearchOut
    candidates: list[CandidateOut]
    stage1_count: int
    stage1_ms: float
    stage2_ms: float
    total_ms: float


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str | None


class MyMatchSideOut(BaseModel):
    id: UUID
    title: str
    image_url: str
    is_mine: bool


class MyMatchOut(BaseModel):
    id: UUID
    query: MyMatchSideOut
    matched: MyMatchSideOut
    rerank_score: float | None
    confirmed_at: datetime


class ConfirmMatchRequest(BaseModel):
    matched_item_id: UUID
    combined_score: float
    rerank_score: float | None = None


class ConfirmMatchResult(BaseModel):
    ok: bool
    contact_email: str | None


class StatsOut(BaseModel):
    users: int
    open_total: int
    lost_total: int
    found_total: int
    matched_total: int
    matches: int
    match_success_rate: float
    cache: dict[str, int]
    latency_samples: int
    latency: dict
    cost: dict
    qdrant: dict
