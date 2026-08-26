"""The coded vocabulary of the DSV formats.

Every enum here is a :class:`DsvEnum`: its *value* is a speaking, stable name
(``"freestyle"``) and its ``code`` is the literal the file uses (``"F"``). The
split matters because this package has two audiences — the JSON that leaves the
API is read by services in other languages, where ``"freestyle"`` is
self-describing and ``"F"`` is a lookup table nobody has; while the reader and a
future writer need the exact file literal.

Codes are matched case-insensitively and with surrounding whitespace ignored, both
of which the spec explicitly permits.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

E = TypeVar("E", bound="DsvEnum")


class DsvEnum(StrEnum):
    """A vocabulary enum with a speaking value and a DSV file code.

    Subclasses declare members as ``NAME = ("speaking_value", "CODE")``. A member
    whose code is ``None`` has no file representation and is expressed by an empty
    attribute — :attr:`ResultStatus.RANKED` is the one such case.
    """

    code: str | None

    def __new__(cls, value: str, code: str | None = None) -> DsvEnum:
        """Build a member carrying both its speaking value and its file code.

        Args:
            value: The speaking, serialised value.
            code: The literal used in DSV files, or ``None`` when the member is
                represented by an empty attribute.

        Returns:
            The enum member.
        """
        member = str.__new__(cls, value)
        member._value_ = value
        member.code = code
        return member

    @classmethod
    def from_code(cls: type[E], raw: str | None) -> E | None:
        """Resolve a raw file literal to its member.

        Args:
            raw: The attribute text from the file; may be ``None`` or blank.

        Returns:
            The matching member, or ``None`` when the value is blank or unknown.
        """
        if raw is None:
            return None
        needle = raw.strip().casefold()
        if not needle:
            return None
        for member in cls:
            if member.code is not None and member.code.casefold() == needle:
                return member
        return None

    @classmethod
    def codes(cls) -> dict[str, str]:
        """Map every file code to its speaking value, for the ``/spec`` endpoint.

        Returns:
            A mapping of DSV code to speaking value, skipping codeless members.
        """
        return {member.code: member.value for member in cls if member.code is not None}


class FileType(DsvEnum):
    """The four DSV list kinds — attribute ``Listart`` of the ``FORMAT`` element.

    The list kind is the single most load-bearing value in a file: it decides which
    element blocks may occur at all and, for a handful of elements, which attribute
    layout applies. It is unchanged from Format 6 to Format 8.
    """

    DEFINITION = ("definition", "Wettkampfdefinitionsliste")
    """The announcement (``-Wk``): sections, events, age groups, fees."""

    CLUB_ENTRIES = ("club_entries", "Vereinsmeldeliste")
    """One club's entries (``-<Verein>-Me``): swimmers, starts, relays, judges."""

    CLUB_RESULTS = ("club_results", "Vereinsergebnisliste")
    """One club's results (``-<Verein>-Pr``)."""

    MEET_RESULTS = ("meet_results", "Wettkampfergebnisliste")
    """The full meet protocol (``-Pr``)."""


class Course(DsvEnum):
    """Pool length — attribute ``Bahnlänge`` of ``VERANSTALTUNG``."""

    SCM_16 = ("scm_16", "16")
    SCM_20 = ("scm_20", "20")
    SCM_25 = ("scm_25", "25")
    SCM_33 = ("scm_33", "33")
    LCM_50 = ("lcm_50", "50")
    OPEN_WATER = ("open_water", "FW")
    OTHER = ("other", "X")


class TimingSystem(DsvEnum):
    """How the meet was timed — attribute ``Zeitmessung`` of ``VERANSTALTUNG``."""

    AUTOMATIC = ("automatic", "AUTOMATISCH")
    SEMI_AUTOMATIC = ("semi_automatic", "HALBAUTOMATISCH")
    MANUAL = ("manual", "HANDZEIT")


class Gender(DsvEnum):
    """Gender of a person — ``M``/``W``/``D`` in the file."""

    MALE = ("male", "M")
    FEMALE = ("female", "W")

    DIVERSE = ("diverse", "D")
    """Format 7 onwards."""


class EventGender(DsvEnum):
    """Gender an event is open to — attribute ``Geschlecht`` of ``WETTKAMPF``."""

    MALE = ("male", "M")
    FEMALE = ("female", "W")
    DIVERSE = ("diverse", "D")
    MIXED = ("mixed", "X")


class Round(DsvEnum):
    """Round of an event — attribute ``Wettkampfart``.

    Together with the event number this identifies an event within a meet: event 12
    prelim and event 12 final are two distinct ``WETTKAMPF`` elements.
    """

    PRELIM = ("prelim", "V")
    SEMI = ("semi", "Z")
    FINAL = ("final", "F")
    TIMED_FINAL = ("timed_final", "E")

    SWIM_OFF = ("swim_off", "A")
    """Ausschwimmen — result lists only."""

    RE_SWIM = ("re_swim", "N")
    """Nachschwimmen — result lists only."""


class Stroke(DsvEnum):
    """Swim stroke — attribute ``Technik`` of ``WETTKAMPF``."""

    FREESTYLE = ("freestyle", "F")
    BACKSTROKE = ("backstroke", "R")
    BREASTSTROKE = ("breaststroke", "B")
    BUTTERFLY = ("butterfly", "S")
    MEDLEY = ("medley", "L")
    OTHER = ("other", "X")


class Exercise(DsvEnum):
    """Form of the swim — attribute ``Ausübung`` of ``WETTKAMPF``.

    Almost every event is ``WHOLE_STROKE``; the remaining members describe the
    technique-training events that appear in youth meets.
    """

    WHOLE_STROKE = ("whole_stroke", "GL")
    LEGS = ("legs", "BE")
    ARMS = ("arms", "AR")
    START = ("start", "ST")
    TURN = ("turn", "WE")
    GLIDE = ("glide", "GB")

    KICKS_PRONE = ("kicks_prone", "KB")
    """Kicks Bauchlage — Format 8 onwards, and only with ``Technik = S``."""

    KICKS_SUPINE = ("kicks_supine", "KR")
    """Kicks Rückenlage — Format 8 onwards, and only with ``Technik = S``."""

    OTHER = ("other", "X")


class AgeClassType(DsvEnum):
    """How an age group is bounded — attribute ``Wertungsklasse``."""

    YEAR_OF_BIRTH = ("year_of_birth", "JG")
    AGE_CLASS = ("age_class", "AK")


class BestListCategory(DsvEnum):
    """Best-list category an event counts towards — attribute ``Bestenliste``."""

    SWIMMING = ("swimming", "SW")
    """Youth and open class — the default."""

    MASTERS = ("masters", "MS")
    KIDS = ("kids", "KG")

    SIMPLIFIED = ("simplified", "EW")
    """Vereinfachter Wettkampf — Format 7 onwards."""

    PARA = ("para", "PA")
    """Para swimming — Format 7 onwards."""

    OPEN_WATER = ("open_water", "FS")
    """Freiwasserschwimmen — Format 6 and earlier; dropped by Format 7 ("Kennzeichen
    Freiwasser bei Zuordnung Bestenliste entfällt"), kept so old files still read."""

    OTHER = ("other", "XX")


class ResultStatus(DsvEnum):
    """Why a swim was not ranked — attribute ``Grund der Nichtwertung``.

    A regularly ranked swim carries :attr:`RANKED`, which the file expresses by an
    empty attribute; every other value forces ``Platz = 0``.
    """

    RANKED = ("ranked", None)
    DISQUALIFIED = ("disqualified", "DS")
    DID_NOT_START = ("did_not_start", "NA")
    WITHDRAWN = ("withdrawn", "AB")
    DID_NOT_FINISH = ("did_not_finish", "AU")
    TIME_LIMIT_EXCEEDED = ("time_limit_exceeded", "ZU")


class EnmStatus(DsvEnum):
    """Status towards the Endkampf-Norm-Meldung — attribute ``ENM`` of a result."""

    NORM_MET = ("norm_met", "E")
    ENM_DUE = ("enm_due", "F")
    NORM_PROVEN = ("norm_proven", "N")


class ProofCourse(DsvEnum):
    """Which course a qualifying time may be proven on — ``NACHWEIS``."""

    SCM_25 = ("scm_25", "25")
    LCM_50 = ("lcm_50", "50")
    OPEN_WATER = ("open_water", "FW")
    ALL = ("all", "AL")


class EntryFeeType(DsvEnum):
    """What an entry fee is charged for — ``MELDEGELD``."""

    FLAT_RATE = ("flat_rate", "Meldegeldpauschale")
    """A flat amount per club."""

    PER_INDIVIDUAL_START = ("per_individual_start", "Einzelmeldegeld")
    PER_RELAY_START = ("per_relay_start", "Staffelmeldegeld")

    PER_EVENT = ("per_event", "Wkmeldegeld")
    """Per-event fee; takes precedence and requires the Wettkampfnr. attribute."""

    PER_TEAM = ("per_team", "Mannschaftmeldegeld")

    PER_PARTICIPANT = ("per_participant", "Teilnehmermeldegeld")
    """A flat amount per entered swimmer — Format 8 onwards."""

    PER_SECTION = ("per_section", "Abschnittspauschale")
    """A flat amount per club per entered section — Format 8 onwards."""


class JudgeGroup(DsvEnum):
    """Qualification group a nominated judge belongs to — ``KARIMELDUNG``."""

    COMPETITION_JUDGE = ("competition_judge", "WKR")
    EVALUATOR = ("evaluator", "AUS")
    REFEREE = ("referee", "SCH")
    ANNOUNCER = ("announcer", "SPR")


class JudgePosition(DsvEnum):
    """Position a judge is nominated or assigned to — ``KARIABSCHNITT``/``KAMPFGERICHT``."""

    REFEREE = ("referee", "SCH")
    STARTER = ("starter", "STA")
    CHIEF_FINISH_JUDGE = ("chief_finish_judge", "ZRO")
    FINISH_JUDGE = ("finish_judge", "ZR")
    CHIEF_TIMEKEEPER = ("chief_timekeeper", "ZNO")
    TIMEKEEPER = ("timekeeper", "ZN")
    RESERVE_TIMEKEEPER = ("reserve_timekeeper", "RZN")
    STROKE_JUDGE = ("stroke_judge", "SR")
    CHIEF_TURN_JUDGE = ("chief_turn_judge", "WRO")
    TURN_JUDGE = ("turn_judge", "WR")
    EVALUATOR = ("evaluator", "AUS")
    ANNOUNCER = ("announcer", "SP")
    PROTOCOL_KEEPER = ("protocol_keeper", "PKF")

    MISCELLANEOUS = ("miscellaneous", "ZBV")
    """Sonstige Kampfrichter. ``KAMPFGERICHT`` only — never a KARIABSCHNITT wish."""

    # The six below are the Format 7 addition "Einführung weiterer Bezeichnungen
    # für Kampfrichter". WKH, like ZBV, is a KAMPFGERICHT position only.
    CLERK_OF_COURSE = ("clerk_of_course", "STO")
    COMPETITION_HELPER = ("competition_helper", "WKH")
    ASSISTANT_REFEREE = ("assistant_referee", "ASCH")
    SAFETY_OFFICER = ("safety_officer", "SIB")
    COURSE_SUPERVISOR = ("course_supervisor", "SAUF")
    SUPPLY_MARSHAL = ("supply_marshal", "VER")
