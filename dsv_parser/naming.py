"""The DSV file-naming convention.

Chapter 2 of the standard prescribes the file name as strictly as it prescribes
the content::

    JJJJ-MM-TT-Ort-Zusatz.DSV7

The date is the **last** section's date, ``Ort`` is the meet city — not the pool
name — truncated to eight characters, and the ``Zusatz`` identifies the list kind.
Spaces and hyphens are dropped and umlauts transliterated (ä→ae, ö→oe, ü→ue,
ß→ss) in both the city and the club name, which is truncated to sixteen.

This module is here because reading a DSV file usually means writing one back, or
at least checking that an uploaded file is named the way the receiving federation
expects — and because the rule is fiddly enough that everyone gets it wrong once.
"""

from __future__ import annotations

import datetime as dt
import re

from .model.enums import FileType

CITY_MAX_LENGTH = 8
CLUB_MAX_LENGTH = 16
FALLBACK = "Unbekannt"

#: Everything the convention strips out — it keeps only ASCII letters and digits.
_DISALLOWED = re.compile(r"[^A-Za-z0-9]")

_TRANSLITERATION = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
)

#: The ``Zusatz`` per list kind. The two club-scoped kinds are prefixed with the
#: normalised club name.
_SUFFIX = {
    FileType.DEFINITION: "Wk",
    FileType.CLUB_ENTRIES: "Me",
    FileType.CLUB_RESULTS: "Pr",
    FileType.MEET_RESULTS: "Pr",
}

#: The list kinds whose Zusatz carries the club name.
_CLUB_SCOPED = frozenset({FileType.CLUB_ENTRIES, FileType.CLUB_RESULTS})


def normalize(raw: str | None, max_length: int) -> str:
    """Apply the convention to one name part.

    Args:
        raw: The raw city or club name; may be ``None``.
        max_length: How many characters to keep.

    Returns:
        The transliterated, stripped and truncated part; :data:`FALLBACK` when
        nothing usable remains.
    """
    if raw is None:
        return FALLBACK
    cleaned = _DISALLOWED.sub("", raw.translate(_TRANSLITERATION))
    return cleaned[:max_length] if cleaned else FALLBACK


def file_name(
    last_section_date: dt.date,
    city: str | None,
    file_type: FileType,
    *,
    club_name: str | None = None,
    version: int = 8,
    zipped: bool = False,
    sequence: int | None = None,
) -> str:
    """Build the conventional file name for one DSV file.

    Args:
        last_section_date: Date of the meet's last section.
        city: The Veranstaltungsort — the city, not the pool.
        file_type: Which of the four list kinds the file is.
        club_name: The club, for the two club-scoped list kinds; ignored otherwise.
        version: The DSV format version, which is also the extension.
        zipped: Whether this is the ZIP-packed ``.DSV8z`` variant (Format 8 only).
        sequence: Discriminator for several files of the same day and city — the
            standard appends it to the city part (``…-Berlin1-Pr.DSV8``).

    Returns:
        The file name, e.g. ``2026-06-13-Berlin-Pr.DSV8``.
    """
    place = normalize(city, CITY_MAX_LENGTH)
    if sequence is not None:
        place = f"{place}{sequence}"
    suffix = _SUFFIX[file_type]
    if file_type in _CLUB_SCOPED:
        suffix = f"{normalize(club_name, CLUB_MAX_LENGTH)}-{suffix}"
    extension = f"DSV{version}{'z' if zipped else ''}"
    return f"{last_section_date:%Y-%m-%d}-{place}-{suffix}.{extension}"
