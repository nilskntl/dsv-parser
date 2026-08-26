"""The data schema: the document, its elements and the coded vocabulary."""

from .document import DsvDocument
from .enums import DsvEnum, FileType

__all__ = ["DsvDocument", "DsvEnum", "FileType"]
