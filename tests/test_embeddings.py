"""Tests for app.core.embeddings.

These load the real CLIP model (downloaded once from HuggingFace) and run CPU
inference, so the module is exercised end-to-end.
"""

from __future__ import annotations

import logging

import numpy as np
import pytest
from PIL import Image

from app.core import embeddings


def _image(seed: int, size: int = 64) -> Image.Image:
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    return Image.fromarray(pixels, mode="RGB")


def test_embed_image_shape_dtype_and_norm():
    vec = embeddings.embed_image(_image(1))
    assert vec.shape == (embeddings.EMBED_DIM,)
    assert vec.dtype == np.float32
    assert np.linalg.norm(vec) == pytest.approx(1.0, abs=1e-4)


def test_embed_text_shape_dtype_and_norm():
    vec = embeddings.embed_text("a black nike backpack with a red logo")
    assert vec.shape == (embeddings.EMBED_DIM,)
    assert vec.dtype == np.float32
    assert np.linalg.norm(vec) == pytest.approx(1.0, abs=1e-4)


def test_image_embedding_is_deterministic():
    img = _image(7)
    assert np.array_equal(embeddings.embed_image(img), embeddings.embed_image(img))


def test_text_embedding_is_deterministic():
    text = "blue hydro flask water bottle"
    assert np.array_equal(embeddings.embed_text(text), embeddings.embed_text(text))


def test_image_batch_matches_individual():
    imgs = [_image(10), _image(11), _image(12)]
    batch = embeddings.embed_image_batch(imgs)
    assert batch.shape == (3, embeddings.EMBED_DIM)
    for i, img in enumerate(imgs):
        assert np.allclose(batch[i], embeddings.embed_image(img), atol=1e-4)


def test_text_batch_matches_individual():
    texts = ["red umbrella", "silver macbook pro", "set of car keys"]
    batch = embeddings.embed_text_batch(texts)
    assert batch.shape == (3, embeddings.EMBED_DIM)
    for i, text in enumerate(texts):
        assert np.allclose(batch[i], embeddings.embed_text(text), atol=1e-4)


def test_empty_batches_return_empty_arrays():
    assert embeddings.embed_image_batch([]).shape == (0, embeddings.EMBED_DIM)
    assert embeddings.embed_text_batch([]).shape == (0, embeddings.EMBED_DIM)


def test_long_text_logs_truncation_warning(caplog):
    long_text = "lost item " * 100
    with caplog.at_level(logging.WARNING, logger="app.core.embeddings"):
        embeddings.embed_text(long_text)
    assert any("truncated" in rec.message for rec in caplog.records)


def test_invalid_image_input_raises():
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed_image(12345)  # type: ignore[arg-type]


def test_inference_counter_increases():
    before = embeddings.inference_count()
    embeddings.embed_text("counter check")
    assert embeddings.inference_count() > before
