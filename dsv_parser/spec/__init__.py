"""The DSV element table and the vocabulary it is written in.

Importing :data:`REGISTRY` is the only thing the reader needs to know about the
format; every attribute order, every version delta and every list-kind variant
lives in :mod:`dsv_parser.spec.elements`.
"""

from .elements import ELEMENTS, POST_PROCESSED, REGISTRY
from .fields import VERSIONS, Attribute, ElementSpec, Kind, Registry

__all__ = [
    "ELEMENTS",
    "POST_PROCESSED",
    "REGISTRY",
    "VERSIONS",
    "Attribute",
    "ElementSpec",
    "Kind",
    "Registry",
]
