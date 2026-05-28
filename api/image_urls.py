"""Resolve the public-facing image URL for an item by environment.

In local dev the LocalImageStorage returns absolute filesystem paths in
``Item.image_url`` — useless to a browser. The API serves images via
``GET /images/<key>`` (mounted in main.py) and rewrites accordingly. In
production the R2 public URL is composed from ``R2_PUBLIC_URL`` + image_key.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.db import Item


def public_image_url(item: Item, base_url: str | None = None) -> str:
    settings = get_settings()
    if settings.environment == "production":
        return f"{settings.r2_public_url.rstrip('/')}/{item.image_key}"
    prefix = (base_url or "").rstrip("/")
    return f"{prefix}/images/{item.image_key}"
