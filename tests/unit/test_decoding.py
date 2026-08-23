"""Bytes to source text: ZIP unwrapping, encoding sniffing, BOM stripping."""

from __future__ import annotations

import io
import zipfile

from dsv_parser.core.decoding import decode
from dsv_parser.core.diagnostics import Diagnostics

PLAIN = "FORMAT: Wettkampfdefinitionsliste;7;\nDATEIENDE\n"


def _zip(payload: bytes, name: str = "meet.DSV8") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, payload)
    return buffer.getvalue()


def test_decode_plain_utf8_reports_utf8() -> None:
    result = decode(PLAIN.encode("utf-8"), Diagnostics())
    assert result.text == PLAIN
    assert result.encoding == "utf-8"
    assert result.zipped is False


def test_decode_strips_utf8_bom() -> None:
    result = decode(b"\xef\xbb\xbf" + PLAIN.encode("utf-8"), Diagnostics())
    assert result.text.startswith("FORMAT")
    assert result.encoding == "utf-8-sig"


def test_decode_falls_back_to_cp1252_with_warning() -> None:
    diagnostics = Diagnostics()
    result = decode("VERANSTALTUNG: Grüße;\n".encode("cp1252"), diagnostics)
    assert "Grüße" in result.text
    assert result.encoding == "cp1252"
    assert any("cp1252" in entry.message for entry in diagnostics.warnings)


def test_decode_unwraps_zip_archive() -> None:
    diagnostics = Diagnostics()
    result = decode(_zip(PLAIN.encode("utf-8")), diagnostics)
    assert result.text == PLAIN
    assert result.zipped is True
    assert result.member == "meet.DSV8"
    assert diagnostics.clean


def test_decode_empty_archive_reports_error() -> None:
    diagnostics = Diagnostics()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    result = decode(buffer.getvalue(), diagnostics)
    assert result.text == ""
    assert not diagnostics.clean


def test_decode_corrupt_archive_reports_error() -> None:
    diagnostics = Diagnostics()
    result = decode(b"PK\x03\x04garbage", diagnostics)
    assert result.text == ""
    assert not diagnostics.clean


def test_decode_encrypted_archive_reports_error() -> None:
    # zipfile raises RuntimeError (not BadZipFile) for an encrypted entry; it
    # must become a diagnostic, not an exception escaping parse_bytes.
    diagnostics = Diagnostics()
    encrypted = bytearray(_zip(PLAIN.encode("utf-8")))
    # Set the encryption bit in the central directory record, which is where
    # zipfile takes the entry's flags from.
    encrypted[encrypted.find(b"PK\x01\x02") + 8] |= 1
    result = decode(bytes(encrypted), diagnostics)
    assert result.text == ""
    assert any("could not be read" in entry.message for entry in diagnostics.errors)


def test_decode_multi_member_archive_warns_and_reads_first() -> None:
    diagnostics = Diagnostics()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.DSV8", PLAIN)
        archive.writestr("b.DSV8", "FORMAT: x;7;\n")
    result = decode(buffer.getvalue(), diagnostics)
    assert result.text == PLAIN
    assert any("2 entries" in entry.message for entry in diagnostics.warnings)
