"""The optional HTTP surface.

Requires the ``api`` extra (``uv sync --extra api``). Run it with::

    uvicorn dsv_parser.api:app --host 0.0.0.0 --port 8000
"""

from .app import app, create_app
from .routes import router

__all__ = ["app", "create_app", "router"]
