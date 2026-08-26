"""Render the element table as documentation.

The table is the specification this parser implements, so the documentation is
generated from it rather than written alongside it — there is no second copy to
drift. Both the CLI's ``spec`` subcommand and the API's ``GET /spec`` render from
here.
"""

from __future__ import annotations

from typing import Any

from ..model.enums import DsvEnum
from .elements import REGISTRY
from .fields import ElementSpec, Kind


def describe_element(spec: ElementSpec) -> dict[str, Any]:
    """Describe one element layout as a JSON-serialisable dict.

    Args:
        spec: The layout.

    Returns:
        A dict with the element name, its target field and its attributes.
    """
    return {
        "element": spec.element,
        "description": spec.description,
        "target": spec.target,
        "repeated": spec.repeated,
        "versions": sorted(spec.versions) if spec.versions else "all",
        "file_types": (sorted(ft.value for ft in spec.file_types) if spec.file_types else "all"),
        "attributes": [
            {
                "position": position + 1,
                "name": attribute.name,
                "german": attribute.german,
                "kind": attribute.kind.value,
                "enum": attribute.enum.__name__ if attribute.enum else None,
                "versions": sorted(attribute.versions) if attribute.versions else "all",
                "file_types": (
                    sorted(ft.value for ft in attribute.file_types)
                    if attribute.file_types
                    else "all"
                ),
            }
            for position, attribute in enumerate(spec.attributes)
        ],
    }


def describe_registry() -> dict[str, Any]:
    """Describe the whole element table plus every vocabulary it references.

    Returns:
        A dict with an ``elements`` list and a ``vocabularies`` mapping of enum
        name to its ``code`` → speaking-value table.
    """
    vocabularies: dict[str, dict[str, str]] = {}
    for spec in REGISTRY:
        for attribute in spec.attributes:
            if attribute.kind is Kind.ENUM and attribute.enum is not None:
                vocabularies.setdefault(attribute.enum.__name__, attribute.enum.codes())
    return {
        "elements": [describe_element(spec) for spec in REGISTRY],
        "vocabularies": dict(sorted(vocabularies.items())),
    }


def render_text() -> str:
    """Render the element table as a plain-text reference for the terminal.

    Returns:
        The table, one element per block, attributes numbered by position.
    """
    lines: list[str] = []
    for spec in REGISTRY:
        scope = []
        if spec.versions:
            scope.append("v" + "/".join(str(v) for v in sorted(spec.versions)))
        if spec.file_types:
            scope.append(", ".join(sorted(ft.value for ft in spec.file_types)))
        suffix = f"  [{'; '.join(scope)}]" if scope else ""
        lines.append(f"{spec.element}{suffix}")
        if spec.description:
            lines.append(f"    {spec.description}")
        for position, attribute in enumerate(spec.attributes, start=1):
            marks = []
            if attribute.versions:
                marks.append("v" + "/".join(str(v) for v in sorted(attribute.versions)))
            if attribute.file_types:
                marks.append(", ".join(sorted(ft.value for ft in attribute.file_types)))
            kind = attribute.enum.__name__ if attribute.enum else attribute.kind.value
            note = f"  ({'; '.join(marks)})" if marks else ""
            lines.append(
                f"    {position:>2}. {attribute.german:<28} {attribute.name:<28} {kind}{note}"
            )
        lines.append("")
    return "\n".join(lines)


def vocabulary_table(enum: type[DsvEnum]) -> str:
    """Render one vocabulary as ``CODE = speaking_value`` lines.

    Args:
        enum: The vocabulary.

    Returns:
        One line per member that has a file code.
    """
    return "\n".join(f"    {code:<20} {value}" for code, value in enum.codes().items())
