"""WSGI entrypoint for production servers such as Gunicorn."""
from __future__ import annotations

from . import create_app

app = create_app()
