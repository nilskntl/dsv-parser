"""The primitive DSV attribute types ("Datentypen" in the spec).

Four scalar shapes carry every non-text value in a DSV file:

============  ================  ==================================================
Spec type     Literal           Python
============  ================  ==================================================
``Zeit``      ``HH:MM:SS,hh``   ``int`` milliseconds (``00:00:00,00`` → ``None``)
``Datum``     ``TT.MM.JJJJ``    :class:`datetime.date`
``Uhrzeit``   ``HH:MM``         :class:`datetime.time`
``Betrag``    ``12,50``         ``int`` euro cents
============  ================  ==================================================

Swim times are milliseconds rather than :class:`~datetime.timedelta` on purpose:
they are compared, summed and stored by every consumer, and an integer survives
JSON, SQL and every client language without a serialisation convention. The
hundredth is the format's resolution, so the value is always a multiple of ten.

Every parser here raises :class:`DsvValueError` on malformed input and returns
``None`` for a blank attribute. Turning that exception into a diagnostic is the
binder's job — a single bad value must never abort a file.
"""

from __future__ import annotations

import datetime as dt

MILLIS_PER_HUNDREDTH = 10
MILLIS_PER_SECOND = 1_000
MILLIS_PER_MINUTE = 60 * MILLIS_PER_SECOND
MILLIS_PER_HOUR = 60 * MILLIS_PER_MINUTE


class DsvValueError(ValueError):
    """A raw attribute value does not match its declared DSV type."""


def parse_swim_time(raw: str) -> int | None:
    """Parse a DSV ``Zeit`` into milliseconds.

    Tolerates a dot instead of the comma decimal separator and surrounding
    whitespace, but nothing looser: the fraction must be exactly two digits
    (``,5`` is ambiguous between five tenths and five hundredths) and minutes and
    seconds must stay below 60 — a signed or out-of-range component would
    otherwise become a silently wrong number of milliseconds. The all-zero time
    is the spec's placeholder for "no time".

    Args:
        raw: The raw attribute text.

    Returns:
        The time in milliseconds, or ``None`` for a blank value or ``00:00:00,00``.

    Raises:
        DsvValueError: If the value is not a well-formed ``Zeit``.
    """
    value = raw.strip()
    if not value:
        return None
    clock, separator, hundredths = value.replace(".", ",").partition(",")
    parts = clock.split(":")
    if (
        not separator
        or len(parts) != 3
        or len(hundredths) != 2
        or not all(part.isascii() and part.isdigit() for part in (*parts, hundredths))
    ):
        raise DsvValueError(f"not a Zeit (HH:MM:SS,hh): {raw!r}")
    hours, minutes, seconds = (int(part) for part in parts)
    fraction = int(hundredths)
    if minutes > 59 or seconds > 59:
        raise DsvValueError(f"not a Zeit (HH:MM:SS,hh): {raw!r}")
    millis = (
        hours * MILLIS_PER_HOUR
        + minutes * MILLIS_PER_MINUTE
        + seconds * MILLIS_PER_SECOND
        + fraction * MILLIS_PER_HUNDREDTH
    )
    return millis or None


def format_swim_time(millis: int | None) -> str:
    """Render milliseconds as a DSV ``Zeit``.

    Args:
        millis: The time in milliseconds, or ``None`` for "no time".

    Returns:
        The formatted ``HH:MM:SS,hh`` literal; ``None`` renders as the
        ``00:00:00,00`` placeholder.
    """
    value = millis or 0
    hundredths = (value // MILLIS_PER_HUNDREDTH) % 100
    seconds = (value // MILLIS_PER_SECOND) % 60
    minutes = (value // MILLIS_PER_MINUTE) % 60
    hours = value // MILLIS_PER_HOUR
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{hundredths:02d}"


def parse_date(raw: str) -> dt.date | None:
    """Parse a DSV ``Datum`` (``TT.MM.JJJJ``).

    Args:
        raw: The raw attribute text.

    Returns:
        The date, or ``None`` for a blank value.

    Raises:
        DsvValueError: If the value is not a well-formed, existing date.
    """
    value = raw.strip()
    if not value:
        return None
    parts = value.split(".")
    if len(parts) != 3:
        raise DsvValueError(f"not a Datum (TT.MM.JJJJ): {raw!r}")
    try:
        day, month, year = (int(part) for part in parts)
        return dt.date(year, month, day)
    except (ValueError, OverflowError) as exc:
        # OverflowError: dt.date rejects a year beyond C-long range with it, not
        # with ValueError, and the reader must not raise on file content.
        raise DsvValueError(f"not a Datum (TT.MM.JJJJ): {raw!r}") from exc


def format_date(value: dt.date | None) -> str:
    """Render a date as a DSV ``Datum``.

    Args:
        value: The date, or ``None``.

    Returns:
        The ``TT.MM.JJJJ`` literal, or an empty string for ``None``.
    """
    return "" if value is None else f"{value.day:02d}.{value.month:02d}.{value.year:04d}"


def parse_clock(raw: str) -> dt.time | None:
    """Parse a DSV ``Uhrzeit`` (``HH:MM``, 24-hour clock).

    Args:
        raw: The raw attribute text.

    Returns:
        The time of day, or ``None`` for a blank value.

    Raises:
        DsvValueError: If the value is not a well-formed time of day.
    """
    value = raw.strip()
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        raise DsvValueError(f"not an Uhrzeit (HH:MM): {raw!r}")
    try:
        hour, minute = (int(part) for part in parts)
        return dt.time(hour, minute)
    except (ValueError, OverflowError) as exc:
        # OverflowError: dt.time rejects an hour beyond C-long range with it, not
        # with ValueError, and the reader must not raise on file content.
        raise DsvValueError(f"not an Uhrzeit (HH:MM): {raw!r}") from exc


def format_clock(value: dt.time | None) -> str:
    """Render a time of day as a DSV ``Uhrzeit``.

    Args:
        value: The time of day, or ``None``.

    Returns:
        The ``HH:MM`` literal, or an empty string for ``None``.
    """
    return "" if value is None else f"{value.hour:02d}:{value.minute:02d}"


def parse_amount_cents(raw: str) -> int | None:
    """Parse a DSV ``Betrag`` into euro cents.

    Tolerates a dot instead of the comma decimal separator, a missing fraction and
    a single-digit fraction (``5,5`` → 550 cents).

    Args:
        raw: The raw attribute text.

    Returns:
        The amount in cents, or ``None`` for a blank value.

    Raises:
        DsvValueError: If the value is not a well-formed amount.
    """
    value = raw.strip()
    if not value:
        return None
    euros_text, _, fraction_text = value.replace(".", ",").partition(",")
    if fraction_text.count(",") or not euros_text.strip():
        raise DsvValueError(f"not a Betrag (12,50): {raw!r}")
    try:
        euros = int(euros_text)
        if not fraction_text:
            cents = 0
        else:
            padded = fraction_text.strip().ljust(2, "0")
            if len(padded) != 2:
                raise DsvValueError(f"not a Betrag (12,50): {raw!r}")
            cents = int(padded)
    except ValueError as exc:
        raise DsvValueError(f"not a Betrag (12,50): {raw!r}") from exc
    sign = -1 if euros_text.strip().startswith("-") else 1
    return euros * 100 + sign * cents


def format_amount_cents(cents: int | None) -> str:
    """Render euro cents as a DSV ``Betrag``.

    Args:
        cents: The amount in cents, or ``None``.

    Returns:
        The ``12,50`` literal, or an empty string for ``None``.
    """
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100},{abs(cents) % 100:02d}"


def parse_integer(raw: str) -> int | None:
    """Parse a plain integer attribute.

    Args:
        raw: The raw attribute text.

    Returns:
        The integer, or ``None`` for a blank value.

    Raises:
        DsvValueError: If the value is not an integer.
    """
    value = raw.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DsvValueError(f"not a number: {raw!r}") from exc


def parse_flag(raw: str) -> bool | None:
    """Parse a ``J``/``N`` flag.

    The tri-state return is deliberate: several elements distinguish an absent
    optional flag ("not declared") from an explicit ``N``.

    Args:
        raw: The raw attribute text.

    Returns:
        ``True`` for ``J``, ``False`` for ``N``, ``None`` when absent.

    Raises:
        DsvValueError: If the value is neither ``J`` nor ``N``.
    """
    value = raw.strip().upper()
    if not value:
        return None
    if value == "J":
        return True
    if value == "N":
        return False
    raise DsvValueError(f"not a J/N flag: {raw!r}")


def parse_sign(raw: str) -> bool | None:
    """Parse a reaction-time sign (``+`` after the signal, ``-`` before it).

    Args:
        raw: The raw attribute text.

    Returns:
        ``True`` when the sign is negative, ``False`` for ``+`` or a blank value.

    Raises:
        DsvValueError: If the value is neither ``+`` nor ``-``.
    """
    value = raw.strip()
    if not value or value == "+":
        return False
    if value == "-":
        return True
    raise DsvValueError(f"not a +/- sign: {raw!r}")
