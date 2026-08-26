"""Source text to element lines."""

from __future__ import annotations

from dsv_parser.core.diagnostics import Diagnostics
from dsv_parser.core.lexer import tokenize


def test_tokenize_splits_element_and_attributes() -> None:
    lines = tokenize("WETTKAMPF: 1;E;1;\n", Diagnostics())
    assert len(lines) == 1
    assert lines[0].element == "WETTKAMPF"
    assert lines[0].attributes == ("1", "E", "1")
    assert lines[0].line == 1


def test_tokenize_consumes_only_the_terminating_semicolon() -> None:
    # "A;B;" is two attributes; "A;B;;" genuinely has an empty third one.
    assert tokenize("X: A;B;\n", Diagnostics())[0].attributes == ("A", "B")
    assert tokenize("X: A;B;;\n", Diagnostics())[0].attributes == ("A", "B", "")


def test_tokenize_strips_trailing_inline_comment() -> None:
    # The regression this module exists for: an inline comment must not become
    # an attribute, or it silently turns into a value the moment the element
    # gains one more attribute in a later format version.
    line = tokenize("ABSCHNITT: 2;16.05.2026;08:45;J; (* relativ *)\n", Diagnostics())[0]
    assert line.attributes == ("2", "16.05.2026", "08:45", "J")


def test_tokenize_strips_comment_between_attributes() -> None:
    line = tokenize("X: A;(* mitten drin *)B;\n", Diagnostics())[0]
    assert line.attributes == ("A", "B")


def test_tokenize_skips_blank_and_comment_only_lines() -> None:
    assert tokenize("\n(* header *)\n   \n", Diagnostics()) == []


def test_tokenize_recognises_dateiende_without_colon() -> None:
    lines = tokenize("DATEIENDE\n", Diagnostics())
    assert lines[0].element == "DATEIENDE"
    assert lines[0].attributes == ()


def test_tokenize_upper_cases_the_element() -> None:
    assert tokenize("wettkampf: 1;\n", Diagnostics())[0].element == "WETTKAMPF"


def test_tokenize_warns_on_a_line_that_is_neither() -> None:
    diagnostics = Diagnostics()
    assert tokenize("nonsense\n", diagnostics) == []
    assert len(diagnostics.warnings) == 1
    assert diagnostics.warnings[0].line == 1


def test_tokenize_reports_one_based_line_numbers() -> None:
    lines = tokenize("(* c *)\n\nX: A;\n", Diagnostics())
    assert lines[0].line == 3


def test_tokenize_keeps_unicode_line_separators_inside_attributes() -> None:
    # str.splitlines would break on U+2028/U+0085 (a web-form paste, or byte 0x85
    # through the latin-1 fallback) and cut the element line in two.
    diagnostics = Diagnostics()
    lines = tokenize("X: Cup\u2028Halle;N\x85ame;\nY: B;\n", diagnostics)
    assert [line.element for line in lines] == ["X", "Y"]
    assert lines[0].attributes == ("Cup\u2028Halle", "N\x85ame")
    assert lines[1].line == 2
    assert diagnostics.clean
