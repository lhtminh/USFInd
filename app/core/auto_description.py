"""Gemini Vision auto-description for lost-and-found posts."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

from app.core import llm

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SCHEMA = {
    "type": "object",
    "properties": {"description": {"type": "string"}},
    "required": ["description"],
}


class AutoDescriptionError(Exception):
    """Raised when an image cannot be read for description."""


def auto_describe(image_bytes: bytes) -> str:
    """Return a short factual description of the item in the image (via Gemini Flash).

    Raises:
        AutoDescriptionError: if the bytes are not a readable image.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise AutoDescriptionError(f"Unreadable image: {exc}") from exc

    system_instruction = (PROMPTS_DIR / "auto_describe.txt").read_text(encoding="utf-8")
    response = llm.cached_call_flash(
        parts=[image, "Describe this item for a lost-and-found post."],
        system_instruction=system_instruction,
        response_schema=_SCHEMA,
    )
    return str(response.get("description", "")).strip()
