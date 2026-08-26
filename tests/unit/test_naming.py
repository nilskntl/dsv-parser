"""The file-naming convention of chapter 2 of the standard."""

from __future__ import annotations

import datetime as dt

import pytest

from dsv_parser.model.enums import FileType
from dsv_parser.naming import CITY_MAX_LENGTH, file_name, normalize

DATE = dt.date(2001, 12, 16)


def test_meet_results_name_follows_the_specification_example() -> None:
    assert (
        file_name(DATE, "Berlin", FileType.MEET_RESULTS, version=7) == "2001-12-16-Berlin-Pr.DSV7"
    )


@pytest.mark.parametrize(
    ("city", "expected"),
    [("Münster", "Muenster"), ("Frankfurt am Main", "Frankfur")],
)
def test_city_is_transliterated_and_truncated(city: str, expected: str) -> None:
    # Both examples are taken verbatim from the standard.
    assert normalize(city, CITY_MAX_LENGTH) == expected


def test_definition_list_uses_the_wk_suffix() -> None:
    assert file_name(DATE, "Berlin", FileType.DEFINITION) == "2001-12-16-Berlin-Wk.DSV8"


def test_club_scoped_kinds_carry_the_club_name() -> None:
    assert (
        file_name(DATE, "Duisburg", FileType.CLUB_ENTRIES, club_name="SV Hansa Adorf", version=7)
        == "2001-12-16-Duisburg-SVHansaAdorf-Me.DSV7"
    )
    assert (
        file_name(DATE, "Duisburg", FileType.CLUB_RESULTS, club_name="SV Hansa Adorf", version=7)
        == "2001-12-16-Duisburg-SVHansaAdorf-Pr.DSV7"
    )


def test_club_name_is_truncated_to_sixteen() -> None:
    # "Schwimmverein Musterstadt 1899" → "SchwimmvereinMusterstadt1899" → 16 chars.
    assert (
        file_name(DATE, "Berlin", FileType.CLUB_ENTRIES, club_name="Schwimmverein Musterstadt 1899")
        == "2001-12-16-Berlin-SchwimmvereinMus-Me.DSV8"
    )


def test_zip_variant_appends_z() -> None:
    assert file_name(DATE, "Berlin", FileType.MEET_RESULTS, zipped=True).endswith(".DSV8z")


def test_sequence_discriminates_same_day_files() -> None:
    assert file_name(DATE, "Berlin", FileType.DEFINITION, sequence=2) == (
        "2001-12-16-Berlin2-Wk.DSV8"
    )


def test_unusable_name_falls_back() -> None:
    assert normalize("---", 8) == "Unbekannt"
    assert normalize(None, 8) == "Unbekannt"
