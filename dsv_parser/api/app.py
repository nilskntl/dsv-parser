"""FastAPI application factory.

The service is a pure function over its request body — no database, no cache, no
background work, no state between requests — so there is no lifespan, no
settings object and nothing to warm up. Keeping it that way is the point: it
scales by replication and it can be embedded in another app with
``app.include_router(dsv_parser.api.router)``.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from .. import __version__
from .routes import router

DESCRIPTION = """
Parses DSV swim-meet interchange files (Format 5 through 8, including ZIP-packed
`.dsv8z`) into a typed JSON document.

The document schema is published in this OpenAPI document, so a client in any
language can be generated from `/openapi.json`. `GET /spec` returns the element
table the parser implements, including every coded vocabulary.
""".strip()


def configure_logging(level: str | None = None) -> None:
    """Install a root log handler.

    uvicorn leaves the root logger without a handler, which silently drops every
    record the package's module loggers emit.

    Args:
        level: The level name; defaults to ``$LOG_LEVEL`` or ``INFO``.
    """
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        force=True,
    )


def create_app() -> FastAPI:
    """Build the application.

    Returns:
        The configured FastAPI app.
    """
    configure_logging()
    application = FastAPI(
        title="DSV Parser",
        description=DESCRIPTION,
        version=__version__,
    )
    application.include_router(router)
    return application


#: Module-level instance for ``uvicorn dsv_parser.api:app``.
app = create_app()
