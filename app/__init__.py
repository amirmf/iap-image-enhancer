"""Application factory for the image rotation service."""
from __future__ import annotations

import logging
import os

from flask import Flask

from .routes import bp as image_blueprint
from . import config 

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration with sane defaults that can be overridden via env vars.
    app.config.setdefault("ROTATION_LANG", os.getenv("ROTATION_LANG", "fas+eng"))
    app.config.setdefault(
        "ROTATION_MIN_SCORE_DIFF",
        int(os.getenv("ROTATION_MIN_SCORE_DIFF", "200")),
    )

    # Basic logging configuration suitable for containerized environments.
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.register_blueprint(image_blueprint)

    return app
