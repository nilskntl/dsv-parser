"""Element line + layout → typed model instance.

This is the generic half of the parser: it knows how to turn positional text into
a typed object given an :class:`~dsv_parser.spec.fields.ElementSpec`, and it knows
nothing whatsoever about any particular DSV element. Every element-specific fact
lives in the table.

The binding contract is tolerant by design, matching the reader's promise that a
single bad value never costs more than that value:

* A value that does not match its declared type becomes ``None`` and an ``ERROR``
  diagnostic naming the line, the attribute position and the spec attribute name.
* An unknown enum code becomes ``None`` and an ``ERROR``.
* Missing trailing attributes are simply absent — writers legitimately truncate
  the optional tail.
* Surplus attributes beyond the layout produce one ``WARNING`` per line. This is
  the signal that catches a version delta the table does not know about yet, so it
  is worth a diagnostic even though nothing is lost.
"""

from __future__ import annotations

from typing import Any

from ..model.elements import DsvElement
from ..model.enums import FileType
from ..spec.fields import Attribute, ElementSpec, Kind
from .diagnostics import Diagnostics
from .lexer import ElementLine
from .values import (
    DsvValueError,
    parse_amount_cents,
    parse_clock,
    parse_date,
    parse_flag,
    parse_integer,
    parse_sign,
    parse_swim_time,
)

#: Coercion for every :class:`~dsv_parser.spec.fields.Kind` except ``ENUM`` and
#: ``TEXT``, both of which need context the table carries.
_SCALARS = {
    Kind.INT: parse_integer,
    Kind.SWIM_TIME: parse_swim_time,
    Kind.DATE: parse_date,
    Kind.CLOCK: parse_clock,
    Kind.AMOUNT: parse_amount_cents,
    Kind.FLAG: parse_flag,
    Kind.SIGN: parse_sign,
}


def bind(
    line: ElementLine,
    spec: ElementSpec,
    version: int | None,
    file_type: FileType | None,
    diagnostics: Diagnostics,
) -> DsvElement:
    """Bind one element line to its model.

    Args:
        line: The tokenized element line.
        spec: The layout to read it with.
        version: The declared format version, steering conditional attributes.
        file_type: The declared list kind, steering conditional attributes.
        diagnostics: Collector for malformed values and surplus attributes.

    Returns:
        The populated model. Never ``None``: an element with only bad values still
        yields an instance, carrying its source line so the caller can find it.
    """
    active = spec.active(version, file_type)
    values: dict[str, Any] = {"source_line": line.line}
    for position, attribute in enumerate(active):
        if position >= len(line.attributes):
            break
        raw = line.attributes[position]
        values[attribute.name] = _coerce(raw, attribute, position, line, diagnostics)
    if len(line.attributes) > len(active):
        surplus = len(line.attributes) - len(active)
        diagnostics.warning(
            f"{surplus} attribute(s) beyond the {len(active)} this layout declares, ignored"
            f" — the file may use a format version this parser does not model yet",
            line=line.line,
            element=line.element,
        )
    return spec.model(**values)


def _coerce(
    raw: str,
    attribute: Attribute,
    position: int,
    line: ElementLine,
    diagnostics: Diagnostics,
) -> object | None:
    """Convert one raw attribute to its declared type.

    Args:
        raw: The raw attribute text, untrimmed.
        attribute: The layout entry describing it.
        position: Zero-based position, for the diagnostic.
        line: The element line, for the diagnostic.
        diagnostics: Collector for a malformed value or unknown code.

    Returns:
        The typed value, or ``None`` when the attribute is blank or unreadable.
    """
    if attribute.kind is Kind.TEXT:
        return raw.strip() or None

    if attribute.kind is Kind.ENUM:
        if attribute.enum is None:  # pragma: no cover - a bug in the element table
            raise TypeError(
                f"attribute {attribute.name!r} of {line.element} is declared ENUM "
                "but names no vocabulary"
            )
        if not raw.strip():
            return None
        member = attribute.enum.from_code(raw)
        if member is None:
            diagnostics.error(
                f"unknown {attribute.enum.__name__} code",
                line=line.line,
                element=line.element,
                attribute=position + 1,
                field=attribute.german,
                value=raw.strip()[:40],
            )
        return member

    try:
        return _SCALARS[attribute.kind](raw)
    except DsvValueError as exc:
        diagnostics.error(
            str(exc),
            line=line.line,
            element=line.element,
            attribute=position + 1,
            field=attribute.german,
            value=raw.strip()[:40],
        )
        return None
