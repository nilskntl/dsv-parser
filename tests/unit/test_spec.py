"""The element table itself — the invariants the reader relies on."""

from __future__ import annotations

import pytest

from dsv_parser.model.document import DsvDocument
from dsv_parser.model.enums import DsvEnum, FileType
from dsv_parser.spec import ELEMENTS, REGISTRY
from dsv_parser.spec.fields import Kind
from dsv_parser.spec.render import describe_registry, render_text


def test_every_attribute_exists_on_its_model() -> None:
    for spec in ELEMENTS:
        fields = set(spec.model.model_fields)
        for attribute in spec.attributes:
            assert attribute.name in fields, f"{spec.element}.{attribute.name}"


def test_every_target_exists_on_the_document() -> None:
    # FORMAT is the one element with no single target: the parser reads it up
    # front and spreads its two attributes over file_type and version.
    fields = DsvDocument.model_fields
    for spec in ELEMENTS:
        if spec.target is None:
            assert spec.element == "FORMAT"
            continue
        assert spec.target in fields, f"{spec.element} → {spec.target}"


def test_repeated_elements_target_a_list_field() -> None:
    for spec in ELEMENTS:
        if spec.target is None:
            continue
        annotation = str(DsvDocument.model_fields[spec.target].annotation)
        assert spec.repeated == annotation.startswith("list["), spec.element


def test_enum_attributes_declare_a_vocabulary() -> None:
    for spec in ELEMENTS:
        for attribute in spec.attributes:
            has_enum = attribute.enum is not None
            assert (attribute.kind is Kind.ENUM) == has_enum, f"{spec.element}.{attribute.name}"


def test_vocabulary_codes_are_unique_within_an_enum() -> None:
    for spec in ELEMENTS:
        for attribute in spec.attributes:
            if attribute.enum is None:
                continue
            codes = [m.code.casefold() for m in attribute.enum if m.code is not None]
            assert len(codes) == len(set(codes)), attribute.enum.__name__


def test_unwrap_names_a_field_of_its_model() -> None:
    for spec in ELEMENTS:
        if spec.unwrap is not None:
            assert spec.unwrap in spec.model.model_fields, spec.element


def test_lookup_prefers_the_more_specific_variant() -> None:
    entries = REGISTRY.lookup("STAFFELPERSON", 7, FileType.CLUB_ENTRIES)
    results = REGISTRY.lookup("STAFFELPERSON", 7, FileType.MEET_RESULTS)
    assert entries is not None and results is not None
    assert len(entries.attributes) == 4
    assert len(results.attributes) > 4


def test_lookup_unknown_element_returns_none() -> None:
    assert REGISTRY.lookup("GIBTESNICHT", 7, None) is None
    assert REGISTRY.knows("GIBTESNICHT") is False
    assert REGISTRY.knows("WETTKAMPF") is True


@pytest.mark.parametrize(
    ("file_type", "expected"),
    [(FileType.CLUB_ENTRIES, 10), (FileType.DEFINITION, 11), (FileType.MEET_RESULTS, 11)],
)
def test_wettkampf_drops_the_best_list_attribute_in_entry_lists(
    file_type: FileType, expected: int
) -> None:
    spec = REGISTRY.lookup("WETTKAMPF", 7, file_type)
    assert spec is not None
    assert len(spec.active(7, file_type)) == expected


# --- the version deltas, one test per line of the official change logs -----


def test_nationalities_arrive_with_format_7() -> None:
    # Verified against real protocols: PNERGEBNIS carries 16 attributes in a
    # Format 6 file and 19 in a Format 7 one.
    spec = REGISTRY.lookup("PNERGEBNIS", 6, FileType.MEET_RESULTS)
    assert spec is not None
    assert len(spec.active(6, FileType.MEET_RESULTS)) == 16
    assert len(spec.active(7, FileType.MEET_RESULTS)) == 19


def test_handicap_arrives_with_format_7() -> None:
    assert REGISTRY.lookup("HANDICAP", 6, FileType.CLUB_ENTRIES) is None
    assert REGISTRY.lookup("HANDICAP", 7, FileType.CLUB_ENTRIES) is not None


def test_format_5_lacks_the_format_6_additions() -> None:
    assert REGISTRY.lookup("NACHWEIS", 5, FileType.DEFINITION) is None
    assert REGISTRY.lookup("PNREAKTION", 5, FileType.MEET_RESULTS) is None
    assert REGISTRY.lookup("STABLOESE", 5, FileType.MEET_RESULTS) is None
    section = REGISTRY.lookup("ABSCHNITT", 5, FileType.DEFINITION)
    assert section is not None
    assert [a.name for a in section.active(5, FileType.DEFINITION)][-1] == "start_time"


def test_format_8_additions_are_absent_from_format_7() -> None:
    bank = REGISTRY.lookup("BANKVERBINDUNG", 7, FileType.DEFINITION)
    coach = REGISTRY.lookup("TRAINER", 7, FileType.CLUB_ENTRIES)
    judge = REGISTRY.lookup("KARIMELDUNG", 7, FileType.CLUB_ENTRIES)
    assert bank is not None and coach is not None and judge is not None
    assert len(bank.active(7, FileType.DEFINITION)) == 3
    assert len(bank.active(8, FileType.DEFINITION)) == 4
    assert len(coach.active(7, FileType.CLUB_ENTRIES)) == 2
    assert len(coach.active(8, FileType.CLUB_ENTRIES)) == 3
    assert len(judge.active(7, FileType.CLUB_ENTRIES)) == 3
    assert len(judge.active(8, FileType.CLUB_ENTRIES)) == 4


def test_club_lastschrift_flag_is_format_8_and_entry_lists_only() -> None:
    spec = REGISTRY.lookup("VEREIN", 8, FileType.CLUB_ENTRIES)
    assert spec is not None
    assert len(spec.active(8, FileType.CLUB_ENTRIES)) == 5
    assert len(spec.active(8, FileType.MEET_RESULTS)) == 4
    assert len(spec.active(7, FileType.CLUB_ENTRIES)) == 4


@pytest.mark.parametrize(
    ("element", "allowed"),
    [
        ("PNMELDUNG", FileType.CLUB_ENTRIES),
        ("PERSON", FileType.CLUB_RESULTS),
        ("STMELDUNG", FileType.CLUB_ENTRIES),
        ("STAFFEL", FileType.CLUB_RESULTS),
        ("PNERGEBNIS", FileType.MEET_RESULTS),
        ("PERSONENERGEBNIS", FileType.CLUB_RESULTS),
        ("STERGEBNIS", FileType.MEET_RESULTS),
        ("STAFFELERGEBNIS", FileType.CLUB_RESULTS),
        ("VERANSTALTUNGSORT", FileType.DEFINITION),
        ("ANSPRECHPARTNER", FileType.CLUB_ENTRIES),
    ],
)
def test_single_list_kind_elements_are_scoped(element: str, allowed: FileType) -> None:
    for file_type in FileType:
        found = REGISTRY.lookup(element, 8, file_type)
        assert (found is not None) == (file_type is allowed), f"{element} in {file_type}"


def test_abschnitt_is_shorter_outside_the_definition_list() -> None:
    spec = REGISTRY.lookup("ABSCHNITT", 7, None)
    assert spec is not None
    assert len(spec.active(7, FileType.DEFINITION)) == 6
    assert len(spec.active(7, FileType.MEET_RESULTS)) == 4


def test_lastschrift_exists_only_in_format_8() -> None:
    assert REGISTRY.lookup("LASTSCHRIFT", 8, FileType.DEFINITION) is not None
    assert REGISTRY.lookup("LASTSCHRIFT", 7, FileType.DEFINITION) is None


def test_render_text_covers_every_element() -> None:
    rendered = render_text()
    for spec in ELEMENTS:
        assert spec.element in rendered


def test_describe_registry_is_json_serialisable() -> None:
    described = describe_registry()
    assert {"elements", "vocabularies"} == set(described)
    assert len(described["elements"]) == len(ELEMENTS)
    assert "Stroke" in described["vocabularies"]


def test_enum_from_code_is_case_insensitive_and_trims() -> None:
    class Sample(DsvEnum):
        A = ("alpha", "AL")

    assert Sample.from_code("  al  ") is Sample.A
    assert Sample.from_code("") is None
    assert Sample.from_code(None) is None
    assert Sample.from_code("nope") is None
