"""Raw bytes to DSV source text.

Three real-world facts sit between a ``.dsv*`` file on disk and the text the lexer
wants, and each one is handled here so no other module has to care:

1. **ZIP packaging.** ``.DSV8z`` (and the occasional ``.DSV7z``) is a ZIP archive
   around a single plain DSV file. Detected by the ``PK\\x03\\x04`` magic, not by
   the file extension — the extension is frequently wrong.
2. **Encoding.** Format 7/8 mandate UTF-8, but Format 5/6 predate that and are
   almost always Windows-1252 (EasyWk on Windows). There is no declaration in the
   file, so the encoding is sniffed: BOM wins, then strict UTF-8, then CP1252.
   A wrong guess yields mojibake rather than an exception, so the fallback is
   reported as a warning and the caller can re-read with an explicit encoding.
3. **Byte-order mark.** Forbidden by the spec and emitted anyway; stripped.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from .diagnostics import Diagnostics

#: A ZIP file starts with one of three "PK" signatures: a local file header
#: (\x03\x04, the normal case), the end-of-central-directory record (\x05\x06, an
#: archive with no entries) or a spanned-archive marker (\x07\x08). Detecting only
#: the first would silently hand an empty archive's bytes to the lexer as text.
ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"

#: Tried in order, strictly, once the BOM check comes up empty. CP1252 leaves five
#: byte values undefined, so even it can fail — :func:`_decode_text` closes with a
#: lossy pass so that :func:`decode` never raises.
ENCODING_CANDIDATES = ("utf-8", "cp1252")


@dataclass(frozen=True, slots=True)
class DecodedSource:
    """The decoded text of one DSV file plus how it got there.

    Attributes:
        text: The DSV source, BOM-stripped, with the original line endings intact.
        encoding: The encoding that was used, for reporting and round-tripping.
        zipped: Whether the input was a ZIP-packed ``.DSV8z``-style archive.
        member: Name of the archive member the text came from, if zipped.
    """

    text: str
    encoding: str
    zipped: bool = False
    member: str | None = None


def decode(content: bytes, diagnostics: Diagnostics) -> DecodedSource:
    """Turn raw file bytes into DSV source text.

    Args:
        content: The raw bytes — either plain DSV text or a ZIP archive around it.
        diagnostics: Collector for archive problems and encoding fallbacks.

    Returns:
        The decoded source. An unreadable archive yields empty text plus an error
        diagnostic rather than an exception, so a batch import can carry on.
    """
    payload, zipped, member = _unzip_if_needed(content, diagnostics)
    text, encoding = _decode_text(payload, diagnostics)
    return DecodedSource(text=text, encoding=encoding, zipped=zipped, member=member)


def _unzip_if_needed(content: bytes, diagnostics: Diagnostics) -> tuple[bytes, bool, str | None]:
    """Unwrap a ZIP-packed DSV file; pass plain content through untouched.

    Args:
        content: The raw bytes.
        diagnostics: Collector for an empty or corrupt archive.

    Returns:
        A triple of (payload bytes, whether it was zipped, archive member name).
    """
    if not content.startswith(ZIP_SIGNATURES):
        return content, False, None
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not names:
                diagnostics.error("ZIP archive contains no file entry")
                return b"", True, None
            if len(names) > 1:
                diagnostics.warning(
                    f"ZIP archive contains {len(names)} entries; reading only {names[0]!r}"
                )
            return archive.read(names[0]), True, names[0]
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
        # RuntimeError: zipfile's complaint about an encrypted entry;
        # NotImplementedError: a compression method the stdlib cannot decompress.
        diagnostics.error(f"ZIP archive could not be read: {exc}")
        return b"", True, None


def _decode_text(payload: bytes, diagnostics: Diagnostics) -> tuple[str, str]:
    """Decode payload bytes, sniffing the encoding and stripping any BOM.

    Args:
        payload: The (already unzipped) text bytes.
        diagnostics: Collector for the non-UTF-8 fallback warning.

    Returns:
        A pair of (decoded text, the encoding name that was used).
    """
    if payload.startswith(UTF8_BOM):
        return payload[len(UTF8_BOM) :].decode("utf-8", errors="replace"), "utf-8-sig"
    for bom, encoding in ((UTF16_LE_BOM, "utf-16-le"), (UTF16_BE_BOM, "utf-16-be")):
        if payload.startswith(bom):
            diagnostics.warning(f"file is {encoding} encoded; the DSV spec mandates UTF-8")
            return payload[len(bom) :].decode(encoding, errors="replace"), encoding
    for encoding in ENCODING_CANDIDATES:
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            continue
        if encoding != "utf-8":
            diagnostics.warning(
                f"file is not valid UTF-8; decoded as {encoding} "
                "(usual for Format 5/6 files written on Windows)"
            )
        return text, encoding
    # Every strict candidate failed (CP1252 leaves 0x81/0x8D/0x8F/0x90/0x9D undefined).
    # Latin-1 maps all 256 byte values, so this pass cannot fail and keeps the readable
    # ASCII backbone of the file — element names, numbers, separators — intact.
    diagnostics.warning("file matches no known encoding; decoded as latin-1, text may be garbled")
    return payload.decode("latin-1"), "latin-1"
