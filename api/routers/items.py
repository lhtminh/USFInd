"""Read endpoints for items: list, get."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.image_urls import public_image_url
from api.schemas import ItemOut
from app.core import db

router = APIRouter(prefix="/api/items", tags=["items"])


def _base_url(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


@router.get("", response_model=list[ItemOut])
def list_items(
    request: Request,
    type: Literal["lost", "found"] | None = None,
    status: Literal["open", "matched", "closed"] = "open",
    limit: int = 50,
    offset: int = 0,
) -> list[ItemOut]:
    rows = db.list_items(type=type, status=status, limit=limit, offset=offset)
    base = _base_url(request)
    return [ItemOut.from_item(item, image_url=public_image_url(item, base)) for item in rows]


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: UUID, request: Request) -> ItemOut:
    item = db.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemOut.from_item(item, image_url=public_image_url(item, _base_url(request)))
