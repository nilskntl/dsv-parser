"""Parse diagnostics: what the tolerant reader had to complain about.

The parser never raises on content problems. Everything it cannot represent, and
everything it had to recover from, is collected here with full provenance (line
number, element, attribute position) so a caller can decide for itself whether a
file is good enough — an import pipeline can mark a file ``PARTIAL`` on errors, a
validation UI can point at the offending line, and a batch job can simply count
them.

Severity is a two-value scale on purpose:

``ERROR``
    Data was lost. The attribute could not be represented and is ``None`` in the
    document; the surrounding element is still kept with everything else intact.
``WARNING``
    An oddity that was recovered without losing data — an unknown element, a
    surplus attribute, a non-UTF-8 encoding, a missing ``DATEIENDE``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """How bad a diagnostic is for the resulting document."""

    ERROR = "error"
    WARNING = "warning"


class Diagnostic(BaseModel):
    """One problem found while reading a DSV file.

    Attributes:
        severity: Whether data was lost (``ERROR``) or merely recovered (``WARNING``).
        message: Human-readable description, in English, without the location prefix.
        line: One-based line number in the decoded file, or ``None`` for
            whole-file problems (encoding, empty archive).
        element: The DSV element constant the problem occurred in, e.g. ``WETTKAMPF``.
        attribute: One-based attribute position within the element, when the
            problem is attribute-scoped.
        field: The spec name of the offending attribute, e.g. ``technik``.
        value: The raw attribute text that could not be read, truncated.
    """

    severity: Severity
    message: str
    line: int | None = None
    element: str | None = None
    attribute: int | None = None
    field: str | None = None
    value: str | None = None

    def render(self) -> str:
        """Format the diagnostic as a single log/CLI line.

        Returns:
            A string of the shape ``error: line 42 (WETTKAMPF#6 technik): …``.
        """
        location = []
        if self.line is not None:
            location.append(f"line {self.line}")
        if self.element is not None:
            scope = self.element
            if self.attribute is not None:
                scope += f"#{self.attribute}"
            if self.field is not None:
                scope += f" {self.field}"
            location.append(f"({scope})")
        prefix = " ".join(location)
        return (
            f"{self.severity.value}: {prefix}: {self.message}"
            if prefix
            else (f"{self.severity.value}: {self.message}")
        )


class Diagnostics(BaseModel):
    """Mutable collector handed through one parse run.

    A plain list would do, but funnelling every report through two named methods
    keeps the severity decision at the call site readable and gives one place to
    add a cap should a pathological file ever produce millions of entries.

    Attributes:
        entries: Every diagnostic in the order it was reported.
    """

    entries: list[Diagnostic] = Field(default_factory=list)

    def error(self, message: str, **location: object) -> None:
        """Record data loss.

        Args:
            message: What went wrong.
            **location: Any of the :class:`Diagnostic` location fields.
        """
        self.entries.append(Diagnostic(severity=Severity.ERROR, message=message, **location))  # type: ignore[arg-type]

    def warning(self, message: str, **location: object) -> None:
        """Record a recovered oddity.

        Args:
            message: What was odd.
            **location: Any of the :class:`Diagnostic` location fields.
        """
        self.entries.append(Diagnostic(severity=Severity.WARNING, message=message, **location))  # type: ignore[arg-type]

    @property
    def errors(self) -> list[Diagnostic]:
        """Only the entries that mean data was lost."""
        return [entry for entry in self.entries if entry.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        """Only the entries that were recovered without data loss."""
        return [entry for entry in self.entries if entry.severity is Severity.WARNING]

    @property
    def clean(self) -> bool:
        """Whether the file parsed without any data loss."""
        return not self.errors
