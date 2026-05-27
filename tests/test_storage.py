"""Tests for app.core.storage: image processing, local FS, and R2 (moto)."""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws
from PIL import Image

from app.core import storage


def _jpeg_bytes(size=(64, 64), color=(10, 20, 30)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _png_rgba_bytes(size=(64, 64)) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", size, (1, 2, 3, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _gif_bytes(size=(16, 16)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (5, 5, 5)).save(buf, format="GIF")
    return buf.getvalue()


def test_process_jpeg_returns_bytes_key_and_type():
    uid, iid = uuid4(), uuid4()
    out, key, content_type = storage.process_uploaded_image(_jpeg_bytes(), uid, iid)
    assert key == f"items/{uid}/{iid}.jpg"
    assert content_type == "image/jpeg"
    assert Image.open(BytesIO(out)).format == "JPEG"


def test_process_downscales_large_image():
    out, _, _ = storage.process_uploaded_image(_jpeg_bytes(size=(2000, 1000)), uuid4(), uuid4())
    assert max(Image.open(BytesIO(out)).size) == storage.MAX_LONGEST_SIDE


def test_process_rgba_outputs_png():
    uid, iid = uuid4(), uuid4()
    out, key, content_type = storage.process_uploaded_image(_png_rgba_bytes(), uid, iid)
    assert key.endswith(".png")
    assert content_type == "image/png"
    assert Image.open(BytesIO(out)).format == "PNG"


def test_process_rejects_oversized():
    too_big = b"\x00" * (storage.MAX_UPLOAD_BYTES + 1)
    with pytest.raises(storage.StorageError, match="5MB"):
        storage.process_uploaded_image(too_big, uuid4(), uuid4())


def test_process_rejects_unreadable():
    with pytest.raises(storage.StorageError):
        storage.process_uploaded_image(b"this is not an image", uuid4(), uuid4())


def test_process_rejects_unsupported_format():
    with pytest.raises(storage.StorageError, match="format"):
        storage.process_uploaded_image(_gif_bytes(), uuid4(), uuid4())


def test_local_storage_roundtrip(tmp_path):
    store = storage.LocalImageStorage(base_dir=tmp_path)
    key = "items/u1/abc.jpg"
    url = store.upload(key, b"bytes", "image/jpeg")
    assert (tmp_path / key).read_bytes() == b"bytes"
    assert url == str((tmp_path / key).resolve())
    store.delete(key)
    assert not (tmp_path / key).exists()


def test_r2_storage_with_moto():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="usfind-images")
        store = storage.R2ImageStorage(
            client=client, bucket="usfind-images", public_url="https://cdn.test/"
        )
        url = store.upload("items/u/i.jpg", b"imgdata", "image/jpeg")
        assert url == "https://cdn.test/items/u/i.jpg"

        obj = client.get_object(Bucket="usfind-images", Key="items/u/i.jpg")
        assert obj["Body"].read() == b"imgdata"

        store.delete("items/u/i.jpg")
        with pytest.raises(client.exceptions.NoSuchKey):
            client.get_object(Bucket="usfind-images", Key="items/u/i.jpg")


def test_local_download_roundtrip(tmp_path):
    store = storage.LocalImageStorage(base_dir=tmp_path)
    store.upload("a/b.jpg", b"xyz", "image/jpeg")
    assert store.download("a/b.jpg") == b"xyz"


def test_local_download_missing_raises(tmp_path):
    store = storage.LocalImageStorage(base_dir=tmp_path)
    with pytest.raises(storage.StorageError):
        store.download("nope.jpg")


def test_r2_download_with_moto():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="usfind-images")
        store = storage.R2ImageStorage(
            client=client, bucket="usfind-images", public_url="https://cdn.test"
        )
        store.upload("k.jpg", b"payload", "image/jpeg")
        assert store.download("k.jpg") == b"payload"


def test_get_storage_returns_local_in_local_env():
    assert isinstance(storage.get_storage(), storage.LocalImageStorage)
