"""Tests for app.core.auto_description with a mocked Gemini SDK."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.core import auto_description, llm


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (48, 48), (12, 34, 56)).save(buf, format="JPEG")
    return buf.getvalue()


def test_auto_describe_returns_stripped_description(monkeypatch):
    monkeypatch.setattr(
        llm, "cached_call_flash", lambda *a, **k: {"description": "  Black Nike backpack  "}
    )
    assert auto_description.auto_describe(_jpeg_bytes()) == "Black Nike backpack"


def test_auto_describe_missing_field_returns_empty(monkeypatch):
    monkeypatch.setattr(llm, "cached_call_flash", lambda *a, **k: {})
    assert auto_description.auto_describe(_jpeg_bytes()) == ""


def test_auto_describe_unreadable_image_raises():
    with pytest.raises(auto_description.AutoDescriptionError):
        auto_description.auto_describe(b"not an image")
