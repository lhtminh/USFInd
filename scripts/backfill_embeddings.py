"""CLI: re-embed and re-index every item whose embedding_status is 'failed'.

Usage:
    python -m scripts.backfill_embeddings
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.items import backfill_failed_embeddings
from app.core.logging_config import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)
    summary = backfill_failed_embeddings()
    print(
        f"Backfill complete: attempted={summary['attempted']} "
        f"succeeded={summary['succeeded']} failed={summary['failed']}"
    )


if __name__ == "__main__":
    main()
