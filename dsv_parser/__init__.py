"""Parser for DSV swim-meet interchange files (Format 5 through 8).

The public surface is deliberately three functions and two types::

    from dsv_parser import parse_file

    result = parse_file("2026-06-13-Berlin-Pr.DSV8")
    print(result.document.meet.name, len(result.document.individual_results))
    for entry in result.diagnostics.entries:
        print(entry.render())

Everything else — the element table, the lexer, the binder — is available for a
caller that needs it, but reading a file needs none of it.
"""

from importlib.metadata import PackageNotFoundError, version

from .core.diagnostics import Diagnostic, Diagnostics, Severity
from .core.parser import ParseResult, parse_bytes, parse_file, parse_text
from .model.document import DsvDocument
from .model.enums import FileType

__all__ = [
    "Diagnostic",
    "Diagnostics",
    "DsvDocument",
    "FileType",
    "ParseResult",
    "Severity",
    "parse_bytes",
    "parse_file",
    "parse_text",
]

#: Read from the installed distribution metadata, so the version lives in exactly one
#: place (``pyproject.toml``, bumped by Release Please) and cannot drift from it.
try:
    __version__ = version("dsv-parser")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare checkout
    __version__ = "1.0.0"
