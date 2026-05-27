"""CLIP image and text embeddings via openai/clip-vit-base-patch32.

The model and processor load once (thread-safe) on first use, on CUDA when
available else CPU. All encoders return float32, L2-normalized vectors so cosine
similarity in Qdrant reduces to a dot product.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

logger = logging.getLogger(__name__)

MODEL_NAME = "openai/clip-vit-base-patch32"
EMBED_DIM = 512
MAX_TEXT_TOKENS = 77

ImageInput = Image.Image | bytes | Path


class EmbeddingError(Exception):
    """Raised when an image/text cannot be read or encoded."""


_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None
_device: str | None = None
_load_lock = threading.Lock()

_inference_count = 0
_count_lock = threading.Lock()


def _load() -> tuple[CLIPModel, CLIPProcessor, str]:
    """Load (once) and return the CLIP model, processor, and device string."""
    global _model, _processor, _device
    if _model is None:
        with _load_lock:
            if _model is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                try:
                    model = CLIPModel.from_pretrained(MODEL_NAME)
                    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
                except Exception as exc:
                    raise EmbeddingError(f"Failed to load CLIP model {MODEL_NAME}: {exc}") from exc
                model.to(device)
                model.eval()
                _model, _processor, _device = model, processor, device
                logger.info("Loaded CLIP model %s on device %s", MODEL_NAME, device)
    return _model, _processor, _device  # type: ignore[return-value]


def _bump_inference_count(n: int) -> None:
    global _inference_count
    with _count_lock:
        _inference_count += n


def inference_count() -> int:
    """Total number of items embedded since process start (for the stats page)."""
    return _inference_count


def _to_pil(image: ImageInput) -> Image.Image:
    """Coerce a PIL image, raw bytes, or filesystem path into an RGB PIL image."""
    try:
        if isinstance(image, Image.Image):
            img = image
        elif isinstance(image, bytes | bytearray):
            img = Image.open(io.BytesIO(bytes(image)))
        elif isinstance(image, Path):
            img = Image.open(image)
        else:
            raise EmbeddingError(f"Unsupported image input type: {type(image)!r}")
        return img.convert("RGB")
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(f"Failed to read image: {exc}") from exc


def _l2_normalize(arr: np.ndarray) -> np.ndarray:
    """L2-normalize rows of a 2-D array, guarding against zero vectors."""
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return (arr / norms).astype(np.float32)


def embed_image_batch(images: list[ImageInput], batch_size: int = 8) -> np.ndarray:
    """Encode images into an (N, 512) float32, L2-normalized array."""
    if not images:
        return np.empty((0, EMBED_DIM), dtype=np.float32)
    model, processor, device = _load()
    pil_images = [_to_pil(im) for im in images]
    chunks: list[np.ndarray] = []
    start = time.perf_counter()
    try:
        with torch.inference_mode():
            for i in range(0, len(pil_images), batch_size):
                batch = pil_images[i : i + batch_size]
                inputs = processor(images=batch, return_tensors="pt").to(device)
                features = model.get_image_features(**inputs)
                chunks.append(features.cpu().numpy())
    except Exception as exc:
        raise EmbeddingError(f"Image embedding failed: {exc}") from exc
    arr = np.concatenate(chunks, axis=0).astype(np.float32)
    _bump_inference_count(len(pil_images))
    logger.debug(
        "Embedded %d image(s) in %.1fms", len(pil_images), (time.perf_counter() - start) * 1000
    )
    return _l2_normalize(arr)


def embed_text_batch(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Encode texts into an (N, 512) float32, L2-normalized array.

    Texts longer than the CLIP 77-token limit are truncated; truncation is
    logged at WARNING level but never raises.
    """
    if not texts:
        return np.empty((0, EMBED_DIM), dtype=np.float32)
    model, processor, device = _load()
    tokenizer = processor.tokenizer
    chunks: list[np.ndarray] = []
    start = time.perf_counter()
    try:
        with torch.inference_mode():
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                for text in batch:
                    token_len = len(tokenizer(text, truncation=False)["input_ids"])
                    if token_len > MAX_TEXT_TOKENS:
                        logger.warning(
                            "Text truncated to %d tokens (was %d)", MAX_TEXT_TOKENS, token_len
                        )
                inputs = processor(
                    text=batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=MAX_TEXT_TOKENS,
                ).to(device)
                features = model.get_text_features(**inputs)
                chunks.append(features.cpu().numpy())
    except Exception as exc:
        raise EmbeddingError(f"Text embedding failed: {exc}") from exc
    arr = np.concatenate(chunks, axis=0).astype(np.float32)
    _bump_inference_count(len(texts))
    logger.debug("Embedded %d text(s) in %.1fms", len(texts), (time.perf_counter() - start) * 1000)
    return _l2_normalize(arr)


def embed_image(image: ImageInput) -> np.ndarray:
    """Encode a single image into a (512,) float32, L2-normalized vector."""
    return embed_image_batch([image])[0]


def embed_text(text: str) -> np.ndarray:
    """Encode a single text into a (512,) float32, L2-normalized vector."""
    return embed_text_batch([text])[0]
