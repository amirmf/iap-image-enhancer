"""HTTP routes for the image rotation API."""
from __future__ import annotations

import logging
from http import HTTPStatus
from io import BytesIO
from typing import Tuple

from flask import Blueprint, Response, current_app, jsonify, request, send_file
from PIL import Image, UnidentifiedImageError

from .rotation import auto_orient_for_ocr

bp = Blueprint("image", __name__)
logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "TIFF": "image/tiff",
    "BMP": "image/bmp",
}


@bp.route("/healthz", methods=["GET"])
def health() -> Tuple[Response, int]:
    """Simple health endpoint for Kubernetes probes."""
    return jsonify({"status": "ok"}), HTTPStatus.OK


@bp.route("/rotate", methods=["POST"])
def rotate() -> Response:
    """Rotate an uploaded image entirely in-memory."""
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Expected multipart/form-data"}), HTTPStatus.BAD_REQUEST

    upload = request.files.get("file")
    if upload is None:
        return jsonify({"error": "Missing form field 'file'"}), HTTPStatus.BAD_REQUEST

    file_bytes = upload.read()
    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty"}), HTTPStatus.BAD_REQUEST

    try:
        original = Image.open(BytesIO(file_bytes))
        original_format = original.format or "PNG"
        if original_format not in SUPPORTED_FORMATS:
            return (
                jsonify({"error": f"Unsupported image format: {original_format}"}),
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
    except UnidentifiedImageError:
        return jsonify({"error": "Invalid image file"}), HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    try:
        rotated_image, *_ = auto_orient_for_ocr(
            file_bytes,
            lang=current_app.config["ROTATION_LANG"],
            min_score_diff=current_app.config["ROTATION_MIN_SCORE_DIFF"],
        )
    except Exception as exc:  # pragma: no cover - logged for observability
        logger.exception("Rotation failed")
        return jsonify({"error": "Failed to rotate image"}), HTTPStatus.INTERNAL_SERVER_ERROR

    buffer = BytesIO()
    rotated_image.save(buffer, format=original_format)
    buffer.seek(0)

    response = send_file(
        buffer,
        mimetype=SUPPORTED_FORMATS[original_format],
        as_attachment=False,
        download_name=f"rotated.{original_format.lower()}",
    )
    response.headers["Cache-Control"] = "no-store"
    return response
