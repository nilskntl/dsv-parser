"""The vocabulary the element table is written in.

A DSV element is fully described by three things: its name, the ordered list of
its attributes, and the conditions under which each attribute is present. Encoding
that as data rather than as code is the one structural decision this parser makes,
and everything else follows from it:

* **Version and list-kind deltas stop being branches.** ``WETTKAMPF`` has a
  best-list attribute in every list kind except the Vereinsmeldeliste, where the
  two qualification attributes shift one position forward. In a hand-written
  parser that is an ``if`` and an index arithmetic bug waiting to happen; here it
  is one ``file_types=`` on one attribute.
* **Adding an element is one table entry**, not a new ``case`` plus a new handler.
* **The spec becomes introspectable.** ``dsv-parser spec`` and ``GET /spec`` render
  the table itself, so the documentation cannot drift from the implementation.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ..model.enums import DsvEnum, FileType

if TYPE_CHECKING:
    from ..model.elements import DsvElement

#: Every format version this parser knows about.
VERSIONS: frozenset[int] = frozenset({5, 6, 7, 8})


def _applies(
    versions: frozenset[int] | None,
    file_types: frozenset[FileType] | None,
    version: int | None,
    file_type: FileType | None,
) -> bool:
    """Whether a versions=/file_types= marked entry is present in a file flavour.

    The one tolerance policy for attributes and elements alike: an unknown
    version or list kind counts as applicable, because the reader has to do
    something with a file whose ``FORMAT`` line it could not read, and keeping
    everything is the reading that loses the least data.

    Args:
        versions: The format versions the entry is declared for, ``None`` for all.
        file_types: The list kinds the entry is declared for, ``None`` for all.
        version: The declared format version, or ``None`` when unknown.
        file_type: The declared list kind, or ``None`` when unknown.

    Returns:
        ``True`` when the entry occupies a position in this file.
    """
    if versions is not None and version is not None and version not in versions:
        return False
    return not (file_types is not None and file_type is not None and file_type not in file_types)


class Kind(Enum):
    """The primitive type of an attribute, as declared by the spec's Datentypen."""

    TEXT = "text"
    """Free text; empty means absent."""

    INT = "int"
    """A plain integer."""

    SWIM_TIME = "swim_time"
    """``Zeit`` (``HH:MM:SS,hh``), carried as milliseconds."""

    DATE = "date"
    """``Datum`` (``TT.MM.JJJJ``)."""

    CLOCK = "clock"
    """``Uhrzeit`` (``HH:MM``)."""

    AMOUNT = "amount"
    """``Betrag``, carried as euro cents."""

    FLAG = "flag"
    """A ``J``/``N`` flag; absent stays distinct from an explicit ``N``."""

    SIGN = "sign"
    """A ``+``/``-`` reaction-time sign."""

    ENUM = "enum"
    """A coded value; the member is resolved via :meth:`DsvEnum.from_code`."""


@dataclass(frozen=True, slots=True)
class Attribute:
    """One positional attribute of an element.

    Attributes:
        name: The field name on the element model.
        kind: The primitive type to coerce the raw text to.
        german: The attribute's name in the DSV specification, kept for the
            generated documentation and for diagnostics a German-speaking user
            can match against the spec PDF.
        enum: The vocabulary for :attr:`Kind.ENUM` attributes.
        versions: The format versions that carry this attribute. ``None`` means
            all of them.
        file_types: The list kinds that carry this attribute. ``None`` means all
            of them. An attribute that drops out shifts every following attribute
            one position forward — which is exactly the intent.
    """

    name: str
    kind: Kind
    german: str
    enum: type[DsvEnum] | None = None
    versions: frozenset[int] | None = None
    file_types: frozenset[FileType] | None = None

    def applies(self, version: int | None, file_type: FileType | None) -> bool:
        """Whether this attribute is present in the given file flavour.

        Delegates to the module's single tolerance policy — see :func:`_applies`.

        Args:
            version: The declared format version, or ``None`` when unknown.
            file_type: The declared list kind, or ``None`` when unknown.

        Returns:
            ``True`` when the attribute occupies a position in this file.
        """
        return _applies(self.versions, self.file_types, version, file_type)


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """The layout of one DSV element line.

    Attributes:
        element: The element constant as it appears in the file, e.g. ``WETTKAMPF``.
        target: The :class:`~dsv_parser.model.document.DsvDocument` field the
            parsed element is stored in — a list field for repeated elements, a
            scalar field otherwise. ``None`` for ``FORMAT``, whose two attributes
            become two document fields and which the parser reads up front.
        model: The pydantic model the attributes are bound to.
        attributes: The attributes in file order.
        repeated: Whether the element may occur many times. A repeated element is
            appended to its target list; a singular one overwrites, with a warning
            on the second occurrence.
        versions: The format versions the element exists in. ``None`` means all.
        file_types: The list kinds the element may appear in. ``None`` means all.
            An element outside its declared list kinds is still parsed — the
            declaration drives validation and documentation, not rejection.
        unwrap: For an element whose whole payload is a single attribute, the model
            field to lift out so the document stores the bare value instead of a
            one-field object.
        description: One line for the generated spec documentation.
    """

    element: str
    target: str | None
    model: type[DsvElement]
    attributes: tuple[Attribute, ...]
    repeated: bool = True
    versions: frozenset[int] | None = None
    file_types: frozenset[FileType] | None = None
    unwrap: str | None = None
    description: str = ""

    def applies(self, version: int | None, file_type: FileType | None) -> bool:
        """Whether this layout is the right one for the given file flavour.

        Delegates to the module's single tolerance policy — see :func:`_applies`.

        Args:
            version: The declared format version, or ``None`` when unknown.
            file_type: The declared list kind, or ``None`` when unknown.

        Returns:
            ``True`` when this spec should be used to read the element.
        """
        return _applies(self.versions, self.file_types, version, file_type)

    def active(self, version: int | None, file_type: FileType | None) -> tuple[Attribute, ...]:
        """The attributes that occupy a position in the given file flavour.

        Args:
            version: The declared format version, or ``None`` when unknown.
            file_type: The declared list kind, or ``None`` when unknown.

        Returns:
            The applicable attributes, in file order.
        """
        return tuple(a for a in self.attributes if a.applies(version, file_type))


@dataclass(frozen=True, slots=True)
class Registry:
    """All element layouts, indexed by element constant.

    An element may have more than one layout — ``STAFFELPERSON`` is a different
    shape in a Vereinsmeldeliste than in a result list. Layouts are tried in
    declaration order and the first applicable one wins, so a specific variant must
    be declared before the general fallback.

    Attributes:
        specs: Every layout, in declaration order.
    """

    specs: tuple[ElementSpec, ...]
    _by_element: dict[str, tuple[ElementSpec, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Build the element index once, at construction."""
        index: dict[str, list[ElementSpec]] = {}
        for spec in self.specs:
            index.setdefault(spec.element, []).append(spec)
        object.__setattr__(self, "_by_element", {key: tuple(value) for key, value in index.items()})

    def lookup(
        self, element: str, version: int | None, file_type: FileType | None
    ) -> ElementSpec | None:
        """Find the layout to read one element line with.

        Args:
            element: The element constant from the file, upper-cased.
            version: The declared format version, or ``None`` when unknown.
            file_type: The declared list kind, or ``None`` when unknown.

        Returns:
            The first applicable layout, or ``None`` when the element is unknown
            to this parser or exists in no applicable variant. With an unknown
            list kind every variant applies; the widest one is returned then,
            honouring the parser's "most permissive layout" diagnostic — the
            declaration-order tie-break alone would pick an arbitrary variant.
        """
        candidates = [
            spec for spec in self._by_element.get(element, ()) if spec.applies(version, file_type)
        ]
        if not candidates:
            return None
        if file_type is None and len(candidates) > 1:
            return max(candidates, key=lambda spec: len(spec.active(version, file_type)))
        return candidates[0]

    def knows(self, element: str) -> bool:
        """Whether the element constant appears in the table at all.

        Distinguishes "unknown element" from "known element, wrong flavour", which
        are very different diagnostics for the person holding the file.

        Args:
            element: The element constant from the file, upper-cased.

        Returns:
            ``True`` when at least one layout declares this element.
        """
        return element in self._by_element

    def __iter__(self) -> Iterator[ElementSpec]:
        """Iterate every layout in declaration order."""
        return iter(self.specs)
