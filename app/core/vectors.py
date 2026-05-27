"""Qdrant vector store: collection management and image/text vector operations.

Two collections (``items_image`` and ``items_text``) hold 512-dim CLIP vectors
with cosine distance and HNSW indexing. Point IDs are the item UUIDs from
Postgres, so a single id addresses an item across both collections and the
relational store.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar
from uuid import UUID

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HasIdCondition,
    HnswConfigDiff,
    MatchValue,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    Range,
    ScoredPoint,
    VectorParams,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION_IMAGE = "items_image"
COLLECTION_TEXT = "items_text"
VECTOR_SIZE = 512

_RETRYABLE = (ResponseHandlingException, ConnectionError, TimeoutError, OSError)

T = TypeVar("T")

_client: QdrantClient | None = None
_client_lock = threading.Lock()


class VectorStoreError(Exception):
    """Raised when a Qdrant operation fails, including after exhausting retries."""


def _retry_on_connection_error(attempts: int = 3, base_delay: float = 0.5) -> Callable:
    """Decorator: retry a Qdrant operation on transient connection errors."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except _RETRYABLE as exc:
                    last_exc = exc
                    if attempt == attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Qdrant connection error in %s (attempt %d/%d): %s; retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            raise VectorStoreError(
                f"{func.__name__} failed after {attempts} attempts: {last_exc}"
            ) from last_exc

        return wrapper

    return decorator


def get_client() -> QdrantClient:
    """Return the lazily-created, process-wide Qdrant client and ensure collections."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                settings = get_settings()
                _client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key or None,
                    timeout=30,
                )
                _ensure_collections(_client)
    return _client


def _ensure_collections(client: QdrantClient) -> None:
    """Idempotently create both collections with HNSW config and payload indexes."""
    for name in (COLLECTION_IMAGE, COLLECTION_TEXT):
        if client.collection_exists(name):
            continue
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            hnsw_config=HnswConfigDiff(m=16, ef_construct=128, full_scan_threshold=10000),
            on_disk_payload=True,
        )
        client.create_payload_index(name, "type", PayloadSchemaType.KEYWORD)
        client.create_payload_index(name, "status", PayloadSchemaType.KEYWORD)
        client.create_payload_index(name, "created_at_ts", PayloadSchemaType.INTEGER)
        logger.info("Created Qdrant collection %s", name)


def ensure_collections() -> None:
    """Public entry point to guarantee collections exist on the active client."""
    _ensure_collections(get_client())


def _upsert(collection: str, item_id: UUID, vector: np.ndarray, payload: dict) -> None:
    client = get_client()
    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=str(item_id),
                vector=np.asarray(vector, dtype=np.float32).tolist(),
                payload=payload,
            )
        ],
    )


@_retry_on_connection_error()
def upsert_image_embedding(item_id: UUID, vector: np.ndarray, payload: dict) -> None:
    """Upsert an item's image embedding into the items_image collection."""
    _upsert(COLLECTION_IMAGE, item_id, vector, payload)


@_retry_on_connection_error()
def upsert_text_embedding(item_id: UUID, vector: np.ndarray, payload: dict) -> None:
    """Upsert an item's text embedding into the items_text collection."""
    _upsert(COLLECTION_TEXT, item_id, vector, payload)


@_retry_on_connection_error()
def get_embeddings(item_id: UUID) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Return (image_vector, text_vector) for an item; either is None if absent."""
    client = get_client()
    point_id = str(item_id)
    image_pts = client.retrieve(COLLECTION_IMAGE, ids=[point_id], with_vectors=True)
    text_pts = client.retrieve(COLLECTION_TEXT, ids=[point_id], with_vectors=True)
    image_vec = np.asarray(image_pts[0].vector, dtype=np.float32) if image_pts else None
    text_vec = np.asarray(text_pts[0].vector, dtype=np.float32) if text_pts else None
    return image_vec, text_vec


@_retry_on_connection_error()
def search_image(
    query_vector: np.ndarray, qdrant_filter: Filter | None, limit: int
) -> list[ScoredPoint]:
    """Cosine search over the image collection, optionally filtered."""
    client = get_client()
    return client.search(
        collection_name=COLLECTION_IMAGE,
        query_vector=np.asarray(query_vector, dtype=np.float32).tolist(),
        query_filter=qdrant_filter,
        limit=limit,
    )


@_retry_on_connection_error()
def search_text(
    query_vector: np.ndarray, qdrant_filter: Filter | None, limit: int
) -> list[ScoredPoint]:
    """Cosine search over the text collection, optionally filtered."""
    client = get_client()
    return client.search(
        collection_name=COLLECTION_TEXT,
        query_vector=np.asarray(query_vector, dtype=np.float32).tolist(),
        query_filter=qdrant_filter,
        limit=limit,
    )


@_retry_on_connection_error()
def delete_item(item_id: UUID) -> None:
    """Remove an item's points from both collections (no longer searchable)."""
    client = get_client()
    selector = PointIdsList(points=[str(item_id)])
    client.delete(COLLECTION_IMAGE, points_selector=selector)
    client.delete(COLLECTION_TEXT, points_selector=selector)


def build_filter(
    item_type: str | None = None,
    status: str | None = None,
    created_after_ts: int | None = None,
    exclude_item_id: UUID | None = None,
) -> Filter | None:
    """Build a Qdrant filter from common item facets; None if no constraints."""
    must: list[Any] = []
    must_not: list[Any] = []
    if item_type is not None:
        must.append(FieldCondition(key="type", match=MatchValue(value=item_type)))
    if status is not None:
        must.append(FieldCondition(key="status", match=MatchValue(value=status)))
    if created_after_ts is not None:
        must.append(FieldCondition(key="created_at_ts", range=Range(gte=created_after_ts)))
    if exclude_item_id is not None:
        must_not.append(HasIdCondition(has_id=[str(exclude_item_id)]))
    if not must and not must_not:
        return None
    return Filter(must=must or None, must_not=must_not or None)


@_retry_on_connection_error()
def collection_stats() -> dict:
    """Return point counts and index status for both collections (for /stats)."""
    client = get_client()
    stats: dict[str, dict[str, Any]] = {}
    for name in (COLLECTION_IMAGE, COLLECTION_TEXT):
        info = client.get_collection(name)
        stats[name] = {
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": str(info.status),
        }
    return stats
