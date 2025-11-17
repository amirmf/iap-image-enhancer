from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _build_image_bytes(color=(255, 0, 0)) -> BytesIO:
    img = Image.new("RGB", (10, 10), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_rotate_success(client, mocker):
    mock_image = Image.new("RGB", (10, 10), "blue")
    mocker.patch("app.routes.auto_orient_for_ocr", return_value=(mock_image, 0, 0, "upright", "high"))

    data = {"file": (_build_image_bytes(), "test.png")}
    res = client.post("/rotate", data=data, content_type="multipart/form-data")

    assert res.status_code == 200
    assert res.mimetype == "image/png"
    assert res.data


def test_rotate_missing_file(client):
    res = client.post("/rotate", data={}, content_type="multipart/form-data")
    assert res.status_code == 400


def test_rotate_invalid_image(client):
    data = {"file": (BytesIO(b"not-an-image"), "bad.txt")}
    res = client.post("/rotate", data=data, content_type="multipart/form-data")
    assert res.status_code == 415
