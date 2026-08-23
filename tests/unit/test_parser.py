"""End-to-end reading of a whole file, against the synthetic fixtures."""

from __future__ import annotations

import datetime as dt
import io
import zipfile

from dsv_parser import parse_bytes, parse_file, parse_text
from dsv_parser.model.enums import (
    Course,
    EntryFeeType,
    Exercise,
    FileType,
    Gender,
    JudgePosition,
    ResultStatus,
    Round,
    Stroke,
    TimingSystem,
)


def test_parses_a_definition_list_cleanly(definition_bytes: bytes) -> None:
    result = parse_bytes(definition_bytes)
    document = result.document

    assert result.clean, [d.render() for d in result.diagnostics.errors]
    assert document.file_type is FileType.DEFINITION
    assert document.version == 7
    assert document.meet is not None
    assert document.meet.name == "1. Synthetisches Sportfest"
    assert document.meet.course is Course.SCM_25
    assert document.meet.timing is TimingSystem.AUTOMATIC


def test_definition_list_populates_the_scalar_header(definition_bytes: bytes) -> None:
    document = parse_bytes(definition_bytes).document

    assert document.organizer_name == "SV Musterstadt"
    assert document.announcement_url == "https://example.org/ausschreibung"
    assert document.remarks == "Keine Nachmeldungen."
    assert document.entry_deadline == dt.datetime(2026, 5, 1, 18, 0)
    assert document.bank_account is not None
    assert document.bank_account.bic == "MUSTDEFF"


def test_definition_list_reads_the_programme(definition_bytes: bytes) -> None:
    document = parse_bytes(definition_bytes).document

    assert [section.number for section in document.sections] == [1, 2]
    assert document.sections[0].admission_time == dt.time(7, 30)
    assert document.sections[0].judges_meeting_time == dt.time(8, 15)
    assert document.sections[0].start_time == dt.time(8, 45)
    assert document.sections[1].relative_timing is True

    assert len(document.events) == 4
    assert document.events[0].distance == 100
    assert document.events[0].stroke is Stroke.BUTTERFLY
    assert document.events[0].round is Round.TIMED_FINAL
    assert document.events[3].qualification_event_number == 3
    assert document.events[3].qualification_round is Round.PRELIM

    assert [fee.fee_type for fee in document.entry_fees] == [
        EntryFeeType.FLAT_RATE,
        EntryFeeType.PER_INDIVIDUAL_START,
    ]
    assert document.entry_fees[0].amount_cents == 1500


def test_parses_a_result_list_cleanly(results_bytes: bytes) -> None:
    result = parse_bytes(results_bytes)
    document = result.document

    assert result.clean, [d.render() for d in result.diagnostics.errors]
    assert document.file_type is FileType.MEET_RESULTS
    assert document.version == 8

    assert len(document.individual_results) == 2
    first = document.individual_results[0]
    assert first.name == "Musterfrau, Mia"
    assert first.time_millis == 72_340
    assert first.place == 1
    assert first.status is None  # empty attribute — a regularly ranked swim

    second = document.individual_results[1]
    assert second.status is ResultStatus.DISQUALIFIED
    assert second.time_millis is None  # 00:00:00,00 is "no time"
    assert second.remark == "Fehlstart"


def test_result_list_reads_relays_and_officials(results_bytes: bytes) -> None:
    document = parse_bytes(results_bytes).document

    assert [j.position for j in document.judge_assignments] == [
        JudgePosition.REFEREE,
        JudgePosition.STARTER,
    ]
    assert len(document.relay_results) == 1
    assert document.relay_results[0].time_millis == 130_000
    assert document.relay_takeoffs[0].negative is True
    assert document.relay_swimmers[0].name == "Musterfrau, Mia"
    assert document.splits[0].time_millis == 34_120
    assert document.reactions[0].negative is False


def test_meet_protocol_clubs_carry_no_direct_debit_flag(results_bytes: bytes) -> None:
    # The Lastschrift flag is a Format 8 addition to the Vereinsmeldeliste only;
    # a Wettkampfergebnisliste's VEREIN has four attributes in every version.
    document = parse_bytes(results_bytes).document
    assert [club.direct_debit_approved for club in document.clubs] == [None, None]


def test_entry_list_shifts_the_wettkampf_attributes(entries_bytes: bytes) -> None:
    # The Vereinsmeldeliste omits the Bestenliste attribute, so the two
    # qualification attributes move one position forward. Getting this wrong
    # silently mis-assigns values rather than failing.
    result = parse_bytes(entries_bytes)
    document = result.document

    assert result.clean, [d.render() for d in result.diagnostics.errors]
    assert document.file_type is FileType.CLUB_ENTRIES
    assert document.events[0].best_list_category is None
    assert document.events[0].gender is not None


def test_entry_list_uses_the_short_staffelperson_shape(entries_bytes: bytes) -> None:
    document = parse_bytes(entries_bytes).document
    leg = document.relay_swimmers[0]
    assert leg.swimmer_local_id == 1
    assert leg.leg_number == 1
    assert leg.name is None


def test_entry_list_reads_coach_and_contact(entries_bytes: bytes) -> None:
    document = parse_bytes(entries_bytes).document
    assert document.contact_person is not None
    assert document.contact_person.email == "tom@example.org"
    assert document.coaches[0].name == "Trainer, Tom"
    assert document.swimmers[0].coach_number == 1


def test_broken_file_still_yields_a_document(broken_bytes: bytes) -> None:
    result = parse_bytes(broken_bytes)

    assert not result.clean
    # Every bad value is isolated: the element survives with the rest intact.
    assert result.document.sections[0].number is None
    assert result.document.sections[0].date is None
    assert result.document.sections[0].judges_meeting_time == dt.time(8, 15)
    assert result.document.events[0].number == 1
    assert result.document.events[0].round is None
    assert result.document.events[0].stroke is None

    messages = [d.message for d in result.diagnostics.entries]
    assert any("unknown element UNBEKANNT" in m for m in messages)
    assert any("not an element line" in m for m in messages)
    assert any("DATEIENDE" in m for m in messages)


def test_missing_format_is_an_error() -> None:
    result = parse_text("VERANSTALTUNG: Ohne Kopf;Ort;25;HANDZEIT;\nDATEIENDE\n")
    assert not result.clean
    assert any("FORMAT" in d.message for d in result.diagnostics.errors)
    # The header is unreadable, so every layout keeps all of its attributes and
    # the rest of the file is still recovered.
    assert result.document.meet is not None
    assert result.document.meet.city == "Ort"


def test_empty_file_is_an_error() -> None:
    result = parse_text("")
    assert not result.clean
    assert result.document.element_counts() == {}


def test_element_after_dateiende_is_ignored() -> None:
    result = parse_text("FORMAT: Wettkampfergebnisliste;7;\nDATEIENDE\nVEREIN: Zu spaet;1;2;GER;\n")
    assert result.document.clubs == []
    assert any("after DATEIENDE" in d.message for d in result.diagnostics.warnings)


def test_duplicate_singular_element_warns_and_keeps_the_last() -> None:
    result = parse_text(
        "FORMAT: Wettkampfergebnisliste;7;\n"
        "VERANSTALTUNG: Erste;A;25;HANDZEIT;\n"
        "VERANSTALTUNG: Zweite;B;50;HANDZEIT;\n"
        "DATEIENDE\n"
    )
    assert result.document.meet is not None
    assert result.document.meet.name == "Zweite"
    assert any("more than once" in d.message for d in result.diagnostics.warnings)


def test_surplus_attributes_warn_about_an_unmodelled_version() -> None:
    result = parse_text("FORMAT: Wettkampfergebnisliste;7;\nVEREIN: A;1;2;GER;J;X;Y;\nDATEIENDE\n")
    assert any("beyond the" in d.message for d in result.diagnostics.warnings)


def test_format_5_is_read_with_a_warning() -> None:
    result = parse_text("FORMAT: Wettkampfdefinitionsliste;5;\nDATEIENDE\n")
    assert result.document.version == 5
    assert any("Format 5" in d.message for d in result.diagnostics.warnings)


def test_unknown_format_version_warns() -> None:
    result = parse_text("FORMAT: Wettkampfdefinitionsliste;9;\nDATEIENDE\n")
    assert any("outside the supported range" in d.message for d in result.diagnostics.warnings)


def test_future_format_version_is_read_with_the_newest_layout() -> None:
    # An unclamped version 9 would fail every versions= marker and collapse the
    # layouts to the bare Format-5 skeleton — a Format 8 VEREIN's fifth
    # attribute would be dropped as surplus instead of bound.
    result = parse_text(
        "FORMAT: Vereinsmeldeliste;9;\nVEREIN: SV Musterstadt;1234;17;GER;J;\nDATEIENDE\n"
    )
    assert result.document.version == 9
    assert result.document.clubs[0].direct_debit_approved is True
    assert not any("beyond the" in d.message for d in result.diagnostics.warnings)


def test_duplicate_format_warns_and_keeps_the_first() -> None:
    # A second FORMAT would contradict every layout decision already made; it
    # must not slip past the duplicate-singular warning just because the main
    # loop skips FORMAT lines.
    result = parse_text(
        "FORMAT: Wettkampfdefinitionsliste;7;\nFORMAT: Vereinsmeldeliste;6;\nDATEIENDE\n"
    )
    assert result.document.file_type is FileType.DEFINITION
    assert result.document.version == 7
    assert any("FORMAT occurs more than once" in d.message for d in result.diagnostics.warnings)


def test_unknown_list_kind_is_an_error_but_parsing_continues() -> None:
    result = parse_text("FORMAT: Phantasieliste;7;\nVERANSTALTUNG: X;Y;25;HANDZEIT;\nDATEIENDE\n")
    assert result.document.file_type is None
    assert not result.clean
    assert result.document.meet is not None


def test_unknown_list_kind_reads_multi_variant_elements_with_the_widest_layout() -> None:
    # STAFFELPERSON is 4 attributes in a Vereinsmeldeliste and 12 in a result
    # list. The FORMAT diagnostic promises the most permissive reading, so the
    # 12-attribute variant must win over declaration order.
    result = parse_text(
        "FORMAT: Phantasieliste;7;\n"
        "STAFFELPERSON: 901;1;E;Musterfrau, Mia;111111;1;W;2010;16;GER;;;\n"
        "DATEIENDE\n"
    )
    leg = result.document.relay_swimmers[0]
    assert leg.name == "Musterfrau, Mia"
    assert not any("beyond the" in d.message for d in result.diagnostics.warnings)


def test_parse_file_reads_from_disk(fixtures) -> None:
    result = parse_file(fixtures / "definition.dsv7")
    assert result.document.file_type is FileType.DEFINITION


def test_parse_bytes_unwraps_a_zipped_file(definition_bytes: bytes) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("meet.DSV8", definition_bytes)
    result = parse_bytes(buffer.getvalue())
    assert result.source.zipped is True
    assert result.document.file_type is FileType.DEFINITION


def test_element_counts_skips_empty_blocks(definition_bytes: bytes) -> None:
    counts = parse_bytes(definition_bytes).document.element_counts()
    assert counts["events"] == 4
    assert "individual_results" not in counts


def test_diagnostic_render_includes_the_location() -> None:
    result = parse_text("FORMAT: Wettkampfergebnisliste;7;\nVEREIN: A;x;2;GER;\nDATEIENDE\n")
    rendered = [d.render() for d in result.diagnostics.errors]
    assert any("line 2" in text and "VEREIN" in text for text in rendered)


# --- version deltas, read end to end ---------------------------------------


def test_format_6_result_list_has_no_nationalities(fixtures) -> None:
    result = parse_file(fixtures / "results.dsv6")
    document = result.document

    assert result.clean, [d.render() for d in result.diagnostics.errors]
    assert document.version == 6
    swim = document.individual_results[0]
    assert swim.time_millis == 72_340
    assert swim.club_dsv_id == 1234
    assert swim.nationality_1 is None
    assert document.relay_swimmers[0].age_class == 16
    assert document.relay_swimmers[0].nationality_1 is None


def test_format_8_entry_list_reads_every_format_8_addition(fixtures) -> None:
    result = parse_file(fixtures / "entries.dsv8")
    document = result.document

    assert result.clean, [d.render() for d in result.diagnostics.errors]
    assert document.clubs[0].direct_debit_approved is True
    assert document.coaches[0].gender is Gender.MALE
    assert document.judge_nominations[0].gender is Gender.FEMALE
    assert document.events[0].exercise is Exercise.KICKS_PRONE
    assert document.swimmers[0].gender is Gender.DIVERSE
    assert document.handicaps[0].start_class == "S9"


def test_format_5_warns_that_its_layouts_are_derived() -> None:
    result = parse_text(
        "FORMAT: Wettkampfdefinitionsliste;5;\n"
        "ABSCHNITT: 1;16.05.2026;07:30;08:15;08:45;\n"
        "DATEIENDE\n"
    )
    # Format 5 has no "Relative Angabe" attribute, so the element is one shorter
    # and the five attributes present must still land in the right fields.
    section = result.document.sections[0]
    assert section.start_time == dt.time(8, 45)
    assert section.relative_timing is None
    assert any("Format 5" in d.message for d in result.diagnostics.warnings)
