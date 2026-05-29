"""Endpoints scoped to the signed-in user: their items and their confirmed matches."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import require_user
from api.image_urls import public_image_url
from api.schemas import ItemOut, MyMatchOut, MyMatchSideOut
from app.core import db
from app.core.config import get_settings
from app.core.db import User

router = APIRouter(prefix="/api/me", tags=["me"])


def _base_url(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


@router.get("/items", response_model=list[ItemOut])
def my_items(request: Request, user: User = Depends(require_user)) -> list[ItemOut]:
    base = _base_url(request)
    return [
        ItemOut.from_item(item, image_url=public_image_url(item, base))
        for item in db.list_user_items(user.id)
    ]


@router.get("/matches", response_model=list[MyMatchOut])
def my_matches(request: Request, user: User = Depends(require_user)) -> list[MyMatchOut]:
    base = _base_url(request)
    rows = db.list_user_matches(user.id)
    out: list[MyMatchOut] = []
    for row in rows:
        out.append(
            MyMatchOut(
                id=row["id"],
                query=MyMatchSideOut(
                    id=row["item_a_id"],
                    title=row["item_a_title"],
                    image_url=_public_url_for(row["item_a_key"], base),
                    is_mine=row["item_a_user_id"] == user.id,
                ),
                matched=MyMatchSideOut(
                    id=row["item_b_id"],
                    title=row["item_b_title"],
                    image_url=_public_url_for(row["item_b_key"], base),
                    is_mine=row["item_b_user_id"] == user.id,
                ),
                rerank_score=row["rerank_score"],
                confirmed_at=row["confirmed_at"],
            )
        )
    return out


def _public_url_for(image_key: str, base: str) -> str:
    """Mirror api.image_urls.public_image_url, but without an Item instance."""
    settings = get_settings()
    if settings.environment == "production":
        return f"{settings.r2_public_url.rstrip('/')}/{image_key}"
    return f"{base.rstrip('/')}/images/{image_key}"
