"""Application configuration loaded and validated from environment variables.

Importing :func:`get_settings` and calling it at startup guarantees the process
fails fast with a human-readable error if any required variable is missing or
malformed, rather than crashing deep inside a request path later.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment.

    Field names map case-insensitively to environment variables (for example
    ``gemini_api_key`` reads ``GEMINI_API_KEY``). A local ``.env`` file is loaded
    when present; real environment variables always take precedence.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenRouter (OpenAI-compatible gateway to many models)
    openrouter_api_key: str = Field(min_length=1)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_flash_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    openrouter_pro_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

    # Postgres (Neon)
    database_url: str = Field(min_length=1)

    # Qdrant vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Redis cache
    redis_url: str = "redis://localhost:6379"

    # Cloudflare R2 object storage
    r2_endpoint: str = Field(min_length=1)
    r2_access_key_id: str = Field(min_length=1)
    r2_secret_access_key: str = Field(min_length=1)
    r2_bucket: str = Field(default="usfind-images", min_length=1)
    r2_public_url: str = Field(min_length=1)

    # Runtime
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    environment: Literal["local", "production"] = "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the validated, cached :class:`Settings` singleton.

    Raises:
        RuntimeError: if any required variable is missing or invalid. The message
            lists every offending field so the whole configuration can be fixed
            in one pass.
    """
    try:
        return Settings()
    except ValidationError as exc:
        details = "\n".join(
            f"  - {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise RuntimeError(
            "Invalid or missing environment configuration:\n"
            f"{details}\n"
            "Copy .env.example to .env and fill in the required values."
        ) from exc
