"""The CLI, driven end to end through its argument vector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsv_parser.cli import main

pytestmark = pytest.mark.integration


def test_parse_writes_the_document_as_json(fixtures: Path, tmp_path: Path, capsys) -> None:
    output = tmp_path / "out.json"
    code = main(["parse", str(fixtures / "definition.dsv7"), "-o", str(output)])
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["file_type"] == "definition"
    assert len(payload["events"]) == 4


def test_parse_writes_to_stdout_by_default(fixtures: Path, capsys) -> None:
    assert main(["parse", str(fixtures / "definition.dsv7"), "--compact", "-q"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == 7


def test_parse_summary_reports_counts(fixtures: Path, capsys) -> None:
    assert main(["parse", str(fixtures / "results.dsv8"), "--summary", "-q"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["elements"]["individual_results"] == 2
    assert payload["errors"] == 0


def test_parse_diagnostics_envelope_wraps_both(fixtures: Path, capsys) -> None:
    assert main(["parse", str(fixtures / "broken.dsv7"), "--diagnostics", "-q"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {"document", "diagnostics"} == set(payload)
    assert payload["diagnostics"]


def test_parse_strict_exits_non_zero_on_data_loss(fixtures: Path) -> None:
    assert main(["parse", str(fixtures / "broken.dsv7"), "--strict", "-q"]) == 1
    assert main(["parse", str(fixtures / "definition.dsv7"), "--strict", "-q"]) == 0


def test_parse_exclude_none_drops_empty_fields(fixtures: Path, capsys) -> None:
    assert main(["parse", str(fixtures / "definition.dsv7"), "--exclude-none", "-q"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "venue" in payload
    assert "individual_results" not in payload or payload["individual_results"] == []


def test_parse_reads_stdin(monkeypatch, fixtures: Path, capsys) -> None:
    class _Stdin:
        buffer = (fixtures / "definition.dsv7").open("rb")

    monkeypatch.setattr("sys.stdin", _Stdin())
    assert main(["parse", "-", "--summary", "-q"]) == 0
    assert json.loads(capsys.readouterr().out)["file_type"] == "definition"


def test_check_reports_and_exits_on_errors(fixtures: Path, capsys) -> None:
    assert main(["check", str(fixtures / "broken.dsv7")]) == 1
    out = capsys.readouterr().out
    assert "error:" in out
    assert "error(s)" in out


def test_check_passes_a_clean_file(fixtures: Path, capsys) -> None:
    assert main(["check", str(fixtures / "results.dsv8")]) == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_spec_prints_the_element_table(capsys) -> None:
    assert main(["spec"]) == 0
    assert "WETTKAMPF" in capsys.readouterr().out


def test_spec_json_is_machine_readable(tmp_path: Path) -> None:
    output = tmp_path / "spec.json"
    assert main(["spec", "--json", "-o", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["elements"]


def test_spec_text_to_file(tmp_path: Path) -> None:
    output = tmp_path / "spec.txt"
    assert main(["spec", "-o", str(output)]) == 0
    assert "WETTKAMPF" in output.read_text(encoding="utf-8")


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_diagnostics_go_to_stderr(fixtures: Path, capsys) -> None:
    main(["parse", str(fixtures / "broken.dsv7"), "--summary"])
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "error:" not in captured.out
