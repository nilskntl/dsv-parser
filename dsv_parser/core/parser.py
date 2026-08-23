"""The reader: raw bytes to a typed :class:`~dsv_parser.model.document.DsvDocument`.

The pipeline is four stages, each in its own module and each testable on its own:

.. code-block:: text

    bytes ──decoding──▶ text ──lexer──▶ element lines ──binder──▶ models ──▶ document
                (zip, encoding)   (comments, split)   (spec table)   (this module)

What is left here is only the part that genuinely needs the whole file in view:
the ``FORMAT`` line has to be read before anything else because the list kind and
version steer every subsequent layout choice, singular elements have to notice a
duplicate, and the ``DATEIENDE`` terminator has to be enforced.

The reader never raises on file content. Everything it cannot do is a diagnostic,
so a batch import gets a partial document plus a precise list of what it lost
rather than an exception and nothing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from ..model.document import DsvDocument
from ..model.elements import DsvElement, EntryDeadline, Format
from ..model.enums import FileType
from ..spec import REGISTRY
from ..spec.fields import VERSIONS, Registry
from .binder import bind
from .decoding import DecodedSource, decode
from .diagnostics import Diagnostics
from .lexer import END_OF_FILE, ElementLine, tokenize


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The outcome of reading one DSV file.

    Attributes:
        document: The best-effort document. Never ``None``, but incomplete when
            :attr:`diagnostics` holds errors.
        diagnostics: Everything the reader had to complain about.
        source: How the bytes were decoded — encoding and ZIP provenance.
    """

    document: DsvDocument
    diagnostics: Diagnostics
    source: DecodedSource

    @property
    def clean(self) -> bool:
        """Whether the file parsed without any data loss."""
        return self.diagnostics.clean


def parse_bytes(content: bytes, *, registry: Registry = REGISTRY) -> ParseResult:
    """Read one DSV file from raw bytes.

    Args:
        content: The file bytes — plain DSV text or a ZIP-packed ``.DSV8z``.
        registry: The element table to read with. Overridable so a caller can
            extend the table without forking the reader.

    Returns:
        The parse result: document plus diagnostics plus decoding provenance.
    """
    diagnostics = Diagnostics()
    source = decode(content, diagnostics)
    lines = tokenize(source.text, diagnostics)
    document = _assemble(lines, registry, diagnostics)
    return ParseResult(document=document, diagnostics=diagnostics, source=source)


def parse_text(text: str, *, registry: Registry = REGISTRY) -> ParseResult:
    """Read one DSV file from already-decoded text.

    Args:
        text: The DSV source.
        registry: The element table to read with.

    Returns:
        The parse result.
    """
    return parse_bytes(text.encode("utf-8"), registry=registry)


def parse_file(path: str | Path, *, registry: Registry = REGISTRY) -> ParseResult:
    """Read one DSV file from disk.

    Args:
        path: Path to the ``.dsv5`` … ``.dsv8``/``.dsv8z`` file.
        registry: The element table to read with.

    Returns:
        The parse result.

    Raises:
        OSError: If the file cannot be read. Unlike content problems, an
            unreadable file is the caller's problem, not a diagnostic.
    """
    return parse_bytes(Path(path).read_bytes(), registry=registry)


def _assemble(
    lines: list[ElementLine], registry: Registry, diagnostics: Diagnostics
) -> DsvDocument:
    """Turn tokenized element lines into a document.

    Args:
        lines: The element lines in file order.
        registry: The element table.
        diagnostics: Collector for structural problems.

    Returns:
        The assembled document.
    """
    document = DsvDocument()
    if not lines:
        diagnostics.error("file contains no elements")
        return document

    version, file_type = _read_format(lines, document, registry, diagnostics)

    seen_singular: set[str] = set()
    terminated = False
    format_seen = False
    for line in lines:
        if line.element == END_OF_FILE:
            terminated = True
            continue
        if terminated:
            diagnostics.warning(f"element {line.element} after DATEIENDE, ignored", line=line.line)
            continue
        if line.element == "FORMAT":
            # The first FORMAT is consumed by _read_format; a second one would
            # contradict every layout decision already made and must not pass
            # silently like the other singular duplicates would not either.
            if format_seen:
                diagnostics.warning(
                    "element FORMAT occurs more than once; the first one wins",
                    line=line.line,
                )
            format_seen = True
            continue
        _dispatch(line, document, registry, version, file_type, seen_singular, diagnostics)

    if not terminated:
        diagnostics.warning("file is not terminated by DATEIENDE")
    return document


def _read_format(
    lines: list[ElementLine],
    document: DsvDocument,
    registry: Registry,
    diagnostics: Diagnostics,
) -> tuple[int | None, FileType | None]:
    """Read the ``FORMAT`` line up front and record it on the document.

    The list kind and version steer which layout every other element is read
    with, so they cannot wait for their turn in the main loop.

    Args:
        lines: The element lines in file order.
        document: The document to record the header on.
        registry: The element table.
        diagnostics: Collector for a missing, misplaced or unreadable header.

    Returns:
        A pair of (format version, list kind), either of which may be ``None``
        when the header could not be read — the layouts then keep every attribute.
    """
    header = next((line for line in lines if line.element == "FORMAT"), None)
    if header is None:
        diagnostics.error("mandatory FORMAT element is missing")
        return None, None
    if header is not lines[0]:
        diagnostics.warning("FORMAT is not the first element of the file", line=header.line)

    spec = registry.lookup("FORMAT", None, None)
    assert spec is not None, "the element table always declares FORMAT"
    parsed = bind(header, spec, None, None, diagnostics)
    assert isinstance(parsed, Format)

    document.file_type = parsed.file_type
    document.version = parsed.version

    if parsed.file_type is None:
        diagnostics.error(
            "unknown Listart; every element is read with its most permissive layout",
            line=header.line,
            element="FORMAT",
            attribute=1,
            field="Listart",
        )
    if parsed.version is None:
        diagnostics.warning(
            "no format version declared; reading as Format 7/8",
            line=header.line,
            element="FORMAT",
        )
    elif parsed.version not in VERSIONS:
        # An unclamped out-of-range version would fail every versions= marker and
        # collapse the layouts to the bare common skeleton — the opposite of what
        # the diagnostic promises. The nearest supported layout loses the least.
        nearest = max(VERSIONS) if parsed.version > max(VERSIONS) else min(VERSIONS)
        diagnostics.warning(
            f"format version {parsed.version} is outside the supported range "
            f"{min(VERSIONS)}–{max(VERSIONS)}; reading with the Format {nearest} layout",
            line=header.line,
            element="FORMAT",
        )
        return nearest, parsed.file_type
    elif parsed.version == 5:
        # The Format 5 layouts are derived from the Format 6 change log rather than
        # from the Format 5 document, which the DSV no longer publishes — see
        # TODO(spec-v5) in dsv_parser.spec.elements. Saying so is the honest
        # alternative to presenting a derived reading as a verified one.
        diagnostics.warning(
            "Format 5 layouts are derived from the Format 6 change log, not from "
            "the Format 5 specification; reaction times carried as a "
            "PNZWISCHENZEIT with Distanz 0 are read as splits, not reactions",
            line=header.line,
            element="FORMAT",
        )
    return parsed.version, parsed.file_type


def _dispatch(
    line: ElementLine,
    document: DsvDocument,
    registry: Registry,
    version: int | None,
    file_type: FileType | None,
    seen_singular: set[str],
    diagnostics: Diagnostics,
) -> None:
    """Read one element line and store it on the document.

    Args:
        line: The element line.
        document: The document under construction.
        registry: The element table.
        version: The declared format version.
        file_type: The declared list kind.
        seen_singular: Element names of the singular elements already stored,
            so a second occurrence can be reported.
        diagnostics: Collector for unknown elements and duplicates.
    """
    spec = registry.lookup(line.element, version, file_type)
    if spec is None:
        if registry.knows(line.element):
            diagnostics.warning(
                f"element {line.element} has no layout for this file kind, ignored",
                line=line.line,
            )
        else:
            diagnostics.warning(f"unknown element {line.element}, ignored", line=line.line)
        return

    parsed = bind(line, spec, version, file_type, diagnostics)
    target = spec.target
    if target is None:  # pragma: no cover - only FORMAT, consumed by _read_format
        return

    if spec.repeated:
        getattr(document, target).append(parsed)
        return

    if spec.element in seen_singular:
        diagnostics.warning(
            f"element {spec.element} occurs more than once; the last one wins",
            line=line.line,
        )
    seen_singular.add(spec.element)
    setattr(document, target, _unwrap(spec.unwrap, spec.element, parsed))


def _unwrap(unwrap: str | None, element: str, parsed: DsvElement) -> object:
    """Reduce a bound element to the value the document field expects.

    Args:
        unwrap: The model field to lift out, for single-attribute elements.
        element: The element constant, for the post-processed special cases.
        parsed: The bound model.

    Returns:
        The value to assign to the document field.
    """
    if unwrap is not None:
        return getattr(parsed, unwrap)
    if element == "MELDESCHLUSS":
        assert isinstance(parsed, EntryDeadline)
        if parsed.date is None:
            return None
        return dt.datetime.combine(parsed.date, parsed.time or dt.time.min)
    return parsed
