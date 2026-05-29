"""Endpoints for items: list, get, create (auth), confirm match (auth)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from api.deps import require_user
from api.image_urls import public_image_url
from api.schemas import ConfirmMatchRequest, ConfirmMatchResult, ItemOut
from app.core import db
from app.core import items as items_core
from app.core.db import User
from app.core.storage import StorageError

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


@router.post("", response_model=ItemOut)
async def create_item(
    request: Request,
    type: Literal["lost", "found"] = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    location: str | None = Form(None),
    ai_description: str | None = Form(None),
    photo: UploadFile = File(...),
    user: User = Depends(require_user),
) -> ItemOut:
    image_bytes = await photo.read()
    try:
        item = items_core.create_item(
            user_id=user.id,
            type=type,
            title=title.strip(),
            description=(description or "").strip() or None,
            location=(location or "").strip() or None,
            uploaded_file=image_bytes,
            ai_description=(ai_description or "").strip() or None,
        )
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ItemOut.from_item(item, image_url=public_image_url(item, _base_url(request)))


@router.post("/{item_id}/confirm", response_model=ConfirmMatchResult)
def confirm_match(
    item_id: UUID,
    payload: ConfirmMatchRequest,
    user: User = Depends(require_user),
) -> ConfirmMatchResult:
    query = db.get_item(item_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query item not found")
    matched = db.get_item(payload.matched_item_id)
    if matched is None:
        raise HTTPException(status_code=404, detail="Matched item not found")

    items_core.confirm_match(
        query_item_id=query.id,
        matched_item_id=matched.id,
        confirmed_by_user_id=user.id,
        combined_score=payload.combined_score,
        rerank_score=payload.rerank_score,
    )
    other_owner_id = matched.user_id if matched.user_id != user.id else query.user_id
    other = db.get_user(other_owner_id)
    return ConfirmMatchResult(ok=True, contact_email=other.email if other else None)
