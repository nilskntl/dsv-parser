"""DSV source text to element lines.

The DSV grammar is deliberately tiny: every meaningful line is
``ELEMENT: attr1;attr2;…;`` and everything between ``(*`` and ``*)`` is a comment.
The one element without a colon is the file terminator ``DATEIENDE``.

Two details are easy to get wrong and are the reason this is its own module:

* **Comments are inline, not line-based.** Real EasyWk output routinely ends a data
  line with ``(* 100m Schmetterling weiblich *)``. A tokenizer that only skips lines
  *starting* with ``(*`` leaves that comment sitting in the last attribute slot,
  where it silently becomes a value as soon as an element gains one more attribute.
  Comments are therefore stripped wherever they occur, before the split.
* **The trailing semicolon is a terminator, not a separator.** ``A;B;`` has two
  attributes, not three, so exactly one trailing empty field is dropped — while
  ``A;B;;`` genuinely has an empty third attribute and must keep it.

Attributes come out trimmed: the spec allows leading and trailing spaces inside an
attribute regardless of its data type, and real files are full of them
(``STAFFELPERSON:2525; 4;4713;1;``). Trimming once here beats trimming in every
value parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .diagnostics import Diagnostics

#: ``(* … *)`` comments, non-greedy and spanning no more than one line (the format
#: has no multi-line comments; treating them as line-local keeps a stray ``(*``
#: from swallowing the rest of the file).
COMMENT = re.compile(r"\(\*.*?\*\)")

#: The three line endings DSV files actually use. Deliberately not
#: ``str.splitlines``, which also breaks on U+2028/U+2029/U+0085/VT/FF — characters
#: that legitimately occur *inside* text attributes (a web-form paste, or byte 0x85
#: through the latin-1 fallback) and must not cut an element line in two.
LINE_BREAK = re.compile(r"\r\n|\r|\n")

#: The file terminator, the only element line without a colon.
END_OF_FILE = "DATEIENDE"


@dataclass(frozen=True, slots=True)
class ElementLine:
    """One tokenized element line.

    Attributes:
        element: The element constant before the colon, upper-cased,
            e.g. ``WETTKAMPF``.
        attributes: The attribute texts in file order, trimmed. Optional
            attributes that were left empty are present as empty strings, so
            positional indexing stays correct.
        line: One-based line number in the decoded file.
        raw: The original line, comments and all, for error messages.
    """

    element: str
    attributes: tuple[str, ...]
    line: int
    raw: str


def tokenize(text: str, diagnostics: Diagnostics) -> list[ElementLine]:
    """Split DSV source text into element lines in file order.

    Blank lines and pure-comment lines are dropped silently; a non-blank line that
    is neither an element nor a comment is dropped with a warning.

    Args:
        text: The decoded DSV source.
        diagnostics: Collector for unparseable lines.

    Returns:
        The element lines, in file order.
    """
    lines: list[ElementLine] = []
    for index, raw in enumerate(LINE_BREAK.split(text)):
        number = index + 1
        stripped = COMMENT.sub("", raw).strip()
        if not stripped:
            continue
        if ":" not in stripped:
            if stripped.upper() == END_OF_FILE:
                lines.append(ElementLine(END_OF_FILE, (), number, raw))
            else:
                diagnostics.warning(
                    f"not an element line, skipped: {_shorten(stripped)}", line=number
                )
            continue
        element, _, tail = stripped.partition(":")
        lines.append(
            ElementLine(
                element=element.strip().upper(),
                attributes=_split_attributes(tail),
                line=number,
                raw=raw,
            )
        )
    return lines


def _split_attributes(tail: str) -> tuple[str, ...]:
    """Split the part after the colon into positional attributes.

    Args:
        tail: Everything after the element's colon, comments already removed.

    Returns:
        The trimmed attribute texts, with the single terminating semicolon
        consumed.
    """
    attributes = [value.strip() for value in tail.split(";")]
    if attributes and not attributes[-1]:
        attributes.pop()
    return tuple(attributes)


def _shorten(raw: str, limit: int = 60) -> str:
    """Truncate line content for a diagnostic message.

    Args:
        raw: The line content.
        limit: Maximum number of characters to keep.

    Returns:
        At most ``limit`` characters, ellipsised when cut.
    """
    return raw if len(raw) <= limit else raw[: limit - 3] + "..."
