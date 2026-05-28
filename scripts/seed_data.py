"""CLI: seed USFind with realistic items, planting matching pairs for demo/benchmark.

Usage:
    python -m scripts.seed_data --num-items 80 --plant-matches 8

Downloads a small pool of free Unsplash images and runs them through the real
``items.create_item`` pipeline (storage + embeddings + Qdrant), so the resulting
data exercises the full retrieval stack end-to-end.
"""

from __future__ import annotations

import argparse
import logging
import random
import urllib.request

from app.core import db, items
from app.core.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger("scripts.seed_data")

# (category_tag, base_title, Unsplash image URL with ?w=800).
_IMAGE_POOL: list[tuple[str, str, str]] = [
    (
        "backpack",
        "black backpack",
        "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800",
    ),
    (
        "water bottle",
        "blue water bottle",
        "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=800",
    ),
    ("keys", "set of keys", "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=800"),
    ("phone", "smartphone", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800"),
    (
        "headphones",
        "wireless headphones",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800",
    ),
    (
        "laptop",
        "silver laptop",
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800",
    ),
    (
        "wallet",
        "brown wallet",
        "https://images.unsplash.com/photo-1627123424574-724758594e93?w=800",
    ),
    (
        "notebook",
        "spiral notebook",
        "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=800",
    ),
    ("glasses", "eyeglasses", "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=800"),
    ("jacket", "denim jacket", "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800"),
    (
        "umbrella",
        "black umbrella",
        "https://images.unsplash.com/photo-1485955869521-b1a4f9d68b5e?w=800",
    ),
    (
        "charger",
        "usb-c charger",
        "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=800",
    ),
]

_LOCATIONS = [
    "Library",
    "MSC",
    "Engineering Building",
    "Marshall Center",
    "Cooper Hall",
    "USF Park",
    "Sun Dome",
]


def _download(url: str, timeout: int = 30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return response.read()


def _create_test_users() -> list:
    return [db.upsert_user(f"seed{i}@usfind.local", f"Seed{i}") for i in range(1, 6)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-items", type=int, default=80)
    parser.add_argument("--plant-matches", type=int, default=8)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)
    db.run_migrations()

    users = _create_test_users()
    rng = random.Random(0)

    created = 0
    planted_pairs = 0

    # Planted matching pairs: same image, one 'lost' and one 'found'.
    for index in range(min(args.plant_matches, len(_IMAGE_POOL))):
        category, base_title, url = _IMAGE_POOL[index]
        try:
            data = _download(url)
        except Exception as exc:
            logger.warning("Skip planted pair %s: %s", url, exc)
            continue
        location = _LOCATIONS[index % len(_LOCATIONS)]
        try:
            items.create_item(
                user_id=users[0].id,
                type="lost",
                title=f"Lost {base_title}",
                description=f"Looks like a {category}",
                location=location,
                uploaded_file=data,
            )
            items.create_item(
                user_id=users[1].id,
                type="found",
                title=f"Found {base_title}",
                description=f"Possibly a {category}",
                location=location,
                uploaded_file=data,
            )
        except Exception as exc:
            logger.warning("Failed to create planted pair for %s: %s", category, exc)
            continue
        created += 2
        planted_pairs += 1

    # Fill remaining slots with random variety.
    while created < args.num_items:
        category, base_title, url = rng.choice(_IMAGE_POOL)
        try:
            data = _download(url)
        except Exception as exc:
            logger.warning("Download failed for %s: %s", url, exc)
            continue
        kind = rng.choice(["lost", "found"])
        try:
            items.create_item(
                user_id=rng.choice(users).id,
                type=kind,
                title=f"{kind.title()} {base_title}",
                description=None,
                location=rng.choice(_LOCATIONS),
                uploaded_file=data,
            )
        except Exception as exc:
            logger.warning("Failed to create item for %s: %s", category, exc)
            continue
        created += 1

    print(f"Seeded {created} item(s), including {planted_pairs} planted matching pair(s).")


if __name__ == "__main__":
    main()
