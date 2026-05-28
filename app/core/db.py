"""PostgreSQL access layer: pooled connections, migration runner, typed helpers.

psycopg 3 uses ``%s`` positional placeholders (the spec's "$1, $2" is shorthand
for "parameterized"). Every query here passes values as parameters — never via
string interpolation — so the layer is injection-safe by construction.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypeVar
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

ItemType = Literal["lost", "found"]
ItemStatus = Literal["open", "matched", "closed"]
EmbeddingStatus = Literal["pending", "ready", "failed"]

_RETRYABLE = (psycopg.OperationalError, psycopg.InterfaceError)

T = TypeVar("T")


class DatabaseError(Exception):
    """Raised when a database operation fails, including after exhausting retries."""


class User(BaseModel):
    id: UUID
    email: str
    name: str | None
    created_at: datetime


class Item(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    description: str | None
    ai_description: str | None
    image_url: str
    image_key: str
    location: str | None
    status: str
    embedding_status: str
    created_at: datetime
    updated_at: datetime
    poster_name: str | None = None


class Match(BaseModel):
    id: UUID
    item_a_id: UUID
    item_b_id: UUID
    confirmed_by_user_id: UUID
    combined_score: float
    rerank_score: float | None
    created_at: datetime


_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def get_pool() -> ConnectionPool:
    """Return the lazily-created, process-wide connection pool (min 2, max 10)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                settings = get_settings()
                _pool = ConnectionPool(
                    conninfo=str(settings.database_url),
                    min_size=2,
                    max_size=10,
                    kwargs={"autocommit": False},
                    open=True,
                )
    return _pool


def close_pool() -> None:
    """Close the pool if open. Primarily for test teardown and clean shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Yield a pooled connection (autocommit off).

    The connection is committed on clean exit and rolled back on exception by the
    pool's own context manager, then returned to the pool.
    """
    pool = get_pool()
    with pool.connection() as conn:
        conn.autocommit = False
        yield conn


def _retry_on_connection_error(attempts: int = 3, base_delay: float = 0.5) -> Callable:
    """Decorator: retry a DB operation on transient connection errors with backoff."""

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
                        "DB connection error in %s (attempt %d/%d): %s; retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            raise DatabaseError(
                f"{func.__name__} failed after {attempts} attempts: {last_exc}"
            ) from last_exc

        return wrapper

    return decorator


def _applied_migrations(conn: psycopg.Connection) -> set[str]:
    """Return the set of already-applied migration filenames (empty if untracked)."""
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.schema_migrations')")
        row = cur.fetchone()
        if row is None or row[0] is None:
            return set()
        cur.execute("SELECT filename FROM schema_migrations")
        return {r[0] for r in cur.fetchall()}


def run_migrations() -> list[str]:
    """Apply every ``*.sql`` file in the migrations dir not yet recorded.

    Files are applied in filename order, each in its own transaction. The
    ``schema_migrations`` table is created by the first migration itself, so the
    runner tolerates its initial absence. Returns the filenames applied this run.
    """
    with get_conn() as conn:
        done = _applied_migrations(conn)

    pending = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.name not in done)
    applied: list[str] = []

    for path in pending:
        sql = path.read_text(encoding="utf-8")
        with get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("Migration failed and was rolled back: %s", path.name)
                raise
        applied.append(path.name)
        logger.info("Applied migration: %s", path.name)

    return applied


@_retry_on_connection_error()
def get_system_stats() -> dict:
    """Aggregate counts powering the public stats page."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM users)::int AS users,
              (SELECT COUNT(*) FROM matches)::int AS matches,
              (SELECT COUNT(*) FROM items WHERE type='lost')::int AS lost_total,
              (SELECT COUNT(*) FROM items WHERE type='lost' AND status='matched')::int
                AS lost_matched,
              (SELECT COUNT(*) FROM items WHERE type='found')::int AS found_total,
              (SELECT COUNT(*) FROM items WHERE status='open')::int AS open_total,
              (SELECT COUNT(*) FROM items WHERE status='matched')::int AS matched_total
            """
        )
        row = cur.fetchone() or {}
        lost_total = row.get("lost_total", 0) or 0
        row["match_success_rate"] = (
            (row.get("lost_matched", 0) or 0) / lost_total if lost_total else 0.0
        )
        return dict(row)


@_retry_on_connection_error()
def get_user(user_id: UUID) -> User | None:
    """Fetch a user row by id, or None if absent."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return User.model_validate(row) if row else None


@_retry_on_connection_error()
def list_user_matches(user_id: UUID) -> list[dict]:
    """List confirmed matches involving any item the user posted or confirmed.

    Each row contains both items' titles/images/owners plus the match record so
    the UI can render both sides without further joins.
    """
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
              m.id, m.combined_score, m.rerank_score, m.created_at AS confirmed_at,
              m.confirmed_by_user_id,
              ia.id AS item_a_id, ia.title AS item_a_title,
              ia.image_url AS item_a_image, ia.user_id AS item_a_user_id,
              ib.id AS item_b_id, ib.title AS item_b_title,
              ib.image_url AS item_b_image, ib.user_id AS item_b_user_id
            FROM matches m
            JOIN items ia ON ia.id = m.item_a_id
            JOIN items ib ON ib.id = m.item_b_id
            WHERE ia.user_id = %s OR ib.user_id = %s OR m.confirmed_by_user_id = %s
            ORDER BY m.created_at DESC
            """,
            (user_id, user_id, user_id),
        )
        return [dict(row) for row in cur.fetchall()]


@_retry_on_connection_error()
def upsert_user(email: str, name: str | None = None) -> User:
    """Insert a user by email, or update the name on conflict. Returns the row."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO users (email, name) VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET name = COALESCE(EXCLUDED.name, users.name)
            RETURNING *
            """,
            (email, name),
        )
        row = cur.fetchone()
        conn.commit()
        return User.model_validate(row)


@_retry_on_connection_error()
def insert_item(
    user_id: UUID,
    type: ItemType,
    title: str,
    description: str | None,
    image_url: str,
    image_key: str,
    location: str | None,
    item_id: UUID | None = None,
    ai_description: str | None = None,
) -> Item:
    """Insert a new item (status 'open', embedding_status 'pending'). Returns the row.

    An explicit ``item_id`` may be supplied so callers can derive the storage key
    from the same id before the row exists; otherwise the database assigns one.
    """
    columns = [
        "user_id",
        "type",
        "title",
        "description",
        "ai_description",
        "image_url",
        "image_key",
        "location",
    ]
    values: list[Any] = [
        user_id,
        type,
        title,
        description,
        ai_description,
        image_url,
        image_key,
        location,
    ]
    if item_id is not None:
        columns.insert(0, "id")
        values.insert(0, item_id)
    # Column names are fixed literals (not user input); values are parameterized.
    query = (
        f"INSERT INTO items ({', '.join(columns)}) "
        f"VALUES ({', '.join(['%s'] * len(values))}) RETURNING *"
    )
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        return Item.model_validate(row)


@_retry_on_connection_error()
def get_item(item_id: UUID) -> Item | None:
    """Fetch a single item joined with its poster's name, or None if absent."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT i.*, u.name AS poster_name
            FROM items i JOIN users u ON u.id = i.user_id
            WHERE i.id = %s
            """,
            (item_id,),
        )
        row = cur.fetchone()
        return Item.model_validate(row) if row else None


@_retry_on_connection_error()
def list_items(
    type: ItemType | None = None,
    status: ItemStatus = "open",
    limit: int = 20,
    offset: int = 0,
) -> list[Item]:
    """List items filtered by optional type and status, newest first, paginated."""
    clauses = ["i.status = %s"]
    params: list[Any] = [status]
    if type is not None:
        clauses.append("i.type = %s")
        params.append(type)
    where = " AND ".join(clauses)
    params.extend([limit, offset])
    # The interpolated `where` is built only from fixed column fragments above;
    # all values are passed as parameters.
    query = (
        "SELECT i.*, u.name AS poster_name "
        "FROM items i JOIN users u ON u.id = i.user_id "
        f"WHERE {where} "
        "ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
    )
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return [Item.model_validate(r) for r in cur.fetchall()]


@_retry_on_connection_error()
def list_user_items(user_id: UUID) -> list[Item]:
    """List all items posted by a user, newest first, regardless of status."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT i.*, u.name AS poster_name
            FROM items i JOIN users u ON u.id = i.user_id
            WHERE i.user_id = %s
            ORDER BY i.created_at DESC
            """,
            (user_id,),
        )
        return [Item.model_validate(r) for r in cur.fetchall()]


@_retry_on_connection_error()
def list_items_by_ids(item_ids: list[UUID]) -> dict[UUID, Item]:
    """Fetch multiple items by id in one query; returns a {id: Item} mapping."""
    if not item_ids:
        return {}
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT i.*, u.name AS poster_name
            FROM items i JOIN users u ON u.id = i.user_id
            WHERE i.id = ANY(%s)
            """,
            (item_ids,),
        )
        return {row["id"]: Item.model_validate(row) for row in cur.fetchall()}


@_retry_on_connection_error()
def list_items_by_embedding_status(status: EmbeddingStatus) -> list[Item]:
    """List items in a given embedding pipeline state (used by backfill)."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT i.*, u.name AS poster_name
            FROM items i JOIN users u ON u.id = i.user_id
            WHERE i.embedding_status = %s
            ORDER BY i.created_at ASC
            """,
            (status,),
        )
        return [Item.model_validate(r) for r in cur.fetchall()]


@_retry_on_connection_error()
def update_item_status(item_id: UUID, status: ItemStatus) -> None:
    """Set an item's lifecycle status ('open' | 'matched' | 'closed')."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE items SET status = %s WHERE id = %s", (status, item_id))
        conn.commit()


@_retry_on_connection_error()
def update_embedding_status(item_id: UUID, status: EmbeddingStatus) -> None:
    """Set an item's embedding pipeline status ('pending' | 'ready' | 'failed')."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE items SET embedding_status = %s WHERE id = %s", (status, item_id))
        conn.commit()


@_retry_on_connection_error()
def insert_match(
    item_a_id: UUID,
    item_b_id: UUID,
    confirmed_by: UUID,
    combined_score: float,
    rerank_score: float | None,
) -> Match:
    """Record a confirmed match between two items. Returns the match row."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO matches
              (item_a_id, item_b_id, confirmed_by_user_id, combined_score, rerank_score)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (item_a_id, item_b_id, confirmed_by, combined_score, rerank_score),
        )
        row = cur.fetchone()
        conn.commit()
        return Match.model_validate(row)
