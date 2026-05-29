"""USFind FastAPI bridge: thin REST layer over app/core/* for the Next.js frontend.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import items as items_router
from api.routers import matches as matches_router
from api.routers import search as search_router
from api.routers import stats as stats_router
from app.core import db
from app.core.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)

settings = get_settings()
configure_logging(settings.log_level, settings.environment)


def _warm_clip() -> None:
    """Pre-load the CLIP model in the background so the first embedding is fast."""
    try:
        from app.core import embeddings

        embeddings._load()
    except Exception:
        logger.warning("CLIP warmup failed; the first embedding will pay the cost.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment != "production" or os.getenv("RUN_MIGRATIONS_ON_BOOT") == "true":
        try:
            db.run_migrations()
        except Exception as exc:
            logger.error("Migrations failed at startup: %s", exc)
    threading.Thread(target=_warm_clip, daemon=True).start()
    yield


app = FastAPI(
    title="USFind API",
    description="REST bridge over app/core/* for the Next.js frontend.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js dev origins by default; tighten via env in prod.
_origins = os.getenv(
    "API_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve locally-stored images (LocalImageStorage writes under ./data/images/).
_data_images = Path("data/images")
_data_images.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_data_images)), name="images")


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


app.include_router(items_router.router)
app.include_router(matches_router.router)
app.include_router(search_router.router)
app.include_router(stats_router.router)
