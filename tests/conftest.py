"""Shared test configuration.

Loads a local ``.env`` (if present) so real credentials like a Neon
``DATABASE_URL`` flow through, then fills dummy values for any still-missing
required settings so :func:`app.core.config.get_settings` validates during tests
that never touch the real services.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/usfind_test")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("R2_ENDPOINT", "https://test.r2.example")
os.environ.setdefault("R2_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("R2_BUCKET", "usfind-images")
os.environ.setdefault("R2_PUBLIC_URL", "https://img.test.example")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("LOG_LEVEL", "INFO")
