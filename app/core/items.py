"""Item creation pipeline: persist the row, store the image, embed, and index.

``create_item`` is the single entry point used by the UI. It generates the item
id up front so the storage key and Qdrant point id all agree, inserts the row as
``embedding_status='pending'``, then embeds and indexes. If anything fails after
the row exists, the item is kept (never deleted) and flipped to ``'failed'`` so
it can be repaired later by ``backfill_failed_embeddings``.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from app.core import db, embeddings, storage, vectors
from app.core.db import Item, ItemType

logger = logging.getLogger(__name__)


def _qdrant_payload(item: Item) -> dict:
    return {
        "item_id": str(item.id),
        "type": item.type,
        "status": item.status,
        "created_at_ts": int(item.created_at.timestamp()),
    }


def _embed_text_source(title: str, description: str | None) -> str:
    return f"{title}. {description or ''}".strip()


def _index_item(item: Item, image_bytes: bytes) -> None:
    """Embed an item's image and text and upsert both into Qdrant."""
    image_vector = embeddings.embed_image(image_bytes)
    text_vector = embeddings.embed_text(_embed_text_source(item.title, item.description))
    payload = _qdrant_payload(item)
    vectors.upsert_image_embedding(item.id, image_vector, payload)
    vectors.upsert_text_embedding(item.id, text_vector, payload)


def create_item(
    user_id: UUID,
    type: ItemType,
    title: str,
    description: str | None,
    location: str | None,
    uploaded_file: object,
    ai_description: str | None = None,
) -> Item:
    """Create an item end-to-end and return it once embeddings are indexed.

    Raises:
        StorageError: if the upload is invalid (before any row is created).
        Exception: re-raised after marking the item 'failed' if embedding or
            indexing fails once the row exists.
    """
    item_id = uuid4()
    image_bytes, key, content_type = storage.process_uploaded_image(uploaded_file, user_id, item_id)
    image_url = storage.get_storage().upload(key, image_bytes, content_type)

    item = db.insert_item(
        user_id=user_id,
        type=type,
        title=title,
        description=description,
        image_url=image_url,
        image_key=key,
        location=location,
        item_id=item_id,
        ai_description=ai_description,
    )

    try:
        _index_item(item, image_bytes)
        db.update_embedding_status(item.id, "ready")
    except Exception:
        logger.exception("Embedding/indexing failed for item %s; marking failed", item.id)
        db.update_embedding_status(item.id, "failed")
        raise

    refreshed = db.get_item(item.id)
    return refreshed if refreshed is not None else item


def confirm_match(
    query_item_id: UUID,
    matched_item_id: UUID,
    confirmed_by_user_id: UUID,
    combined_score: float,
    rerank_score: float | None,
) -> db.Match:
    """Record a confirmed match, close both items, and remove them from Qdrant."""
    match = db.insert_match(
        query_item_id,
        matched_item_id,
        confirmed_by_user_id,
        combined_score,
        rerank_score,
    )
    db.update_item_status(query_item_id, "matched")
    db.update_item_status(matched_item_id, "matched")
    try:
        vectors.delete_item(query_item_id)
        vectors.delete_item(matched_item_id)
    except Exception:
        logger.exception("Failed to remove matched items from Qdrant (DB state already matched)")
    return match


def backfill_failed_embeddings() -> dict[str, int]:
    """Retry embedding + indexing for every item marked 'failed'.

    Returns a summary dict with attempted/succeeded/failed counts. Individual
    failures are logged and counted but never abort the run.
    """
    failed = db.list_items_by_embedding_status("failed")
    store = storage.get_storage()
    summary = {"attempted": 0, "succeeded": 0, "failed": 0}

    for item in failed:
        summary["attempted"] += 1
        try:
            image_bytes = store.download(item.image_key)
            _index_item(item, image_bytes)
            db.update_embedding_status(item.id, "ready")
            summary["succeeded"] += 1
        except Exception:
            logger.exception("Backfill failed for item %s", item.id)
            summary["failed"] += 1

    logger.info("Backfill complete: %s", summary)
    return summary
