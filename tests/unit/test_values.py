"""The primitive DSV attribute types."""

from __future__ import annotations

import datetime as dt

import pytest

from dsv_parser.core.values import (
    DsvValueError,
    format_amount_cents,
    format_clock,
    format_date,
    format_swim_time,
    parse_amount_cents,
    parse_clock,
    parse_date,
    parse_flag,
    parse_integer,
    parse_sign,
    parse_swim_time,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00:01:12,34", 72_340),
        ("01:00:00,00", 3_600_000),
        ("00:00:00,01", 10),
        ("00:00:34.12", 34_120),
        ("  00:00:05,00  ", 5_000),
    ],
)
def test_parse_swim_time_valid_literal_returns_millis(raw: str, expected: int) -> None:
    assert parse_swim_time(raw) == expected


def test_parse_swim_time_all_zero_returns_none() -> None:
    assert parse_swim_time("00:00:00,00") is None


def test_parse_swim_time_blank_returns_none() -> None:
    assert parse_swim_time("   ") is None


@pytest.mark.parametrize("raw", ["00:00:00", "1:2", "abc", "00:00:xx,00", "00:00:00;00"])
def test_parse_swim_time_malformed_raises(raw: str) -> None:
    with pytest.raises(DsvValueError):
        parse_swim_time(raw)


@pytest.mark.parametrize(
    "raw", ["00:00:25,5", "00:00:25,345", "00:-1:30,00", "00:99:99,00", "00:00:01,-50"]
)
def test_parse_swim_time_lax_component_raises_instead_of_guessing(raw: str) -> None:
    # Each of these used to parse to a silently wrong number of milliseconds:
    # a one-digit fraction read as hundredths, negative or >59 minutes/seconds
    # folded into the total. Wrong-but-plausible times corrupt rankings, so they
    # must be a diagnostic, not a value.
    with pytest.raises(DsvValueError):
        parse_swim_time(raw)


def test_format_swim_time_round_trip_preserves_value() -> None:
    assert format_swim_time(parse_swim_time("00:01:12,34")) == "00:01:12,34"


def test_format_swim_time_none_renders_placeholder() -> None:
    assert format_swim_time(None) == "00:00:00,00"


def test_parse_date_valid_literal_returns_date() -> None:
    assert parse_date("16.05.2026") == dt.date(2026, 5, 16)


@pytest.mark.parametrize("raw", ["32.13.2026", "2026-05-16", "16.05", "x.y.z"])
def test_parse_date_malformed_raises(raw: str) -> None:
    with pytest.raises(DsvValueError):
        parse_date(raw)


def test_parse_date_huge_year_raises_dsv_error_not_overflow() -> None:
    # dt.date raises OverflowError (not ValueError) beyond the C-long range; it
    # must still surface as DsvValueError so the reader never raises on content.
    with pytest.raises(DsvValueError):
        parse_date("01.01.99999999999999999999")


def test_format_date_round_trip_preserves_value() -> None:
    assert format_date(parse_date("01.02.2026")) == "01.02.2026"


def test_format_date_none_returns_empty() -> None:
    assert format_date(None) == ""


def test_parse_clock_valid_literal_returns_time() -> None:
    assert parse_clock("08:45") == dt.time(8, 45)


@pytest.mark.parametrize("raw", ["25:99", "8", "08:45:00", "99999999999999999999:00"])
def test_parse_clock_malformed_raises(raw: str) -> None:
    with pytest.raises(DsvValueError):
        parse_clock(raw)


def test_format_clock_round_trip_preserves_value() -> None:
    assert format_clock(parse_clock("08:45")) == "08:45"
    assert format_clock(None) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("15,00", 1500), ("3,5", 350), ("12", 1200), ("12.50", 1250), ("-2,50", -250)],
)
def test_parse_amount_cents_valid_literal_returns_cents(raw: str, expected: int) -> None:
    assert parse_amount_cents(raw) == expected


@pytest.mark.parametrize("raw", ["1,2,3", "abc", ",50"])
def test_parse_amount_cents_malformed_raises(raw: str) -> None:
    with pytest.raises(DsvValueError):
        parse_amount_cents(raw)


def test_format_amount_cents_round_trip_preserves_value() -> None:
    assert format_amount_cents(parse_amount_cents("15,00")) == "15,00"
    assert format_amount_cents(None) == ""


def test_format_amount_cents_negative_round_trips() -> None:
    # Floor division on negative cents used to render -550 as "-6,50".
    assert format_amount_cents(parse_amount_cents("-2,50")) == "-2,50"
    assert format_amount_cents(-550) == "-5,50"
    assert format_amount_cents(-50) == "-0,50"


def test_parse_integer_blank_returns_none() -> None:
    assert parse_integer("") is None


def test_parse_integer_not_a_number_raises() -> None:
    with pytest.raises(DsvValueError):
        parse_integer("eins")


def test_parse_flag_tri_state_distinguishes_absent_from_no() -> None:
    assert parse_flag("J") is True
    assert parse_flag("n") is False
    assert parse_flag("") is None


def test_parse_flag_other_value_raises() -> None:
    with pytest.raises(DsvValueError):
        parse_flag("Y")


def test_parse_sign_defaults_to_positive() -> None:
    assert parse_sign("") is False
    assert parse_sign("+") is False
    assert parse_sign("-") is True


def test_parse_sign_other_value_raises() -> None:
    with pytest.raises(DsvValueError):
        parse_sign("*")
