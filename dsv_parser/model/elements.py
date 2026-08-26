"""One pydantic model per DSV element.

These are the leaves of the data schema: each class mirrors exactly one element
line of a DSV file, with the attribute order of the spec preserved in the field
order. Field names are English and speaking; the German element and attribute
names live in the spec tables (:mod:`dsv_parser.spec`), which is the only place
that has to change when a format version moves an attribute.

Every field is optional. That is not laziness — the same element carries a
different attribute count depending on format version and list kind, optional
attributes are routinely left empty, and the reader is tolerant by contract: a
value it cannot represent becomes ``None`` plus a diagnostic, never an exception.
Callers that need a guarantee should validate the assembled
:class:`~dsv_parser.model.document.DsvDocument`, not the individual line.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from .enums import (
    AgeClassType,
    BestListCategory,
    Course,
    EnmStatus,
    EntryFeeType,
    EventGender,
    Exercise,
    FileType,
    Gender,
    JudgeGroup,
    JudgePosition,
    ProofCourse,
    ResultStatus,
    Round,
    Stroke,
    TimingSystem,
)


class DsvElement(BaseModel):
    """Base for every element model.

    Attributes:
        source_line: One-based line number the element was read from. Kept on the
            model so a consumer can point a user back at the file — the reason the
            models are not plain dataclasses.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_line: int | None = None


# --- Single-attribute wrappers --------------------------------------------


class ScalarText(DsvElement):
    """An element whose whole payload is one free-text attribute.

    ``AUSSCHREIBUNGIMNETZ``, ``VERANSTALTER`` and ``BESONDERES`` share this shape.
    They are unwrapped onto a plain string field of the document, so the model
    exists only to keep them in the element table like everything else.
    """

    value: str | None = None


class ScalarFlag(DsvElement):
    """An element whose whole payload is one ``J``/``N`` flag — ``LASTSCHRIFT``."""

    value: bool | None = None


class EntryDeadline(DsvElement):
    """``MELDESCHLUSS`` — the closing date and clock, merged by the assembler."""

    date: dt.date | None = None
    time: dt.time | None = None


# --- File header ----------------------------------------------------------


class Format(DsvElement):
    """``FORMAT`` — the mandatory first element: list kind and format version."""

    file_type: FileType | None = None
    version: int | None = None


class Generator(DsvElement):
    """``ERZEUGER`` — the software that wrote the file."""

    software: str | None = None
    version: str | None = None
    contact: str | None = None


class MeetInfo(DsvElement):
    """``VERANSTALTUNG`` — meet name, city, pool length, timing."""

    name: str | None = None
    city: str | None = None
    course: Course | None = None
    timing: TimingSystem | None = None


class Venue(DsvElement):
    """``VERANSTALTUNGSORT`` — the pool and how to reach it."""

    name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    nation: str | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None


class Host(DsvElement):
    """``AUSRICHTER`` — the organising club and its contact."""

    name: str | None = None
    contact_name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    nation: str | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None


class Contact(DsvElement):
    """``MELDEADRESSE`` / ``ANSPRECHPARTNER`` — the two share one attribute layout."""

    name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    nation: str | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None


class BankAccount(DsvElement):
    """``BANKVERBINDUNG`` — where entry fees are paid."""

    bank_name: str | None = None
    iban: str | None = None
    bic: str | None = None
    account_holder: str | None = None


class ProofOfTime(DsvElement):
    """``NACHWEIS`` — the window and course a qualifying time may come from."""

    valid_from: dt.date | None = None
    valid_until: dt.date | None = None
    course: ProofCourse | None = None


# --- Programme ------------------------------------------------------------


class Section(DsvElement):
    """``ABSCHNITT`` — one session of the meet.

    The definition list carries the admission and judges'-briefing times; every
    other list kind carries only the start time.
    """

    number: int | None = None
    date: dt.date | None = None
    admission_time: dt.time | None = None
    judges_meeting_time: dt.time | None = None
    start_time: dt.time | None = None
    relative_timing: bool | None = None


class Event(DsvElement):
    """``WETTKAMPF`` — one event of the programme, in programme order."""

    number: int | None = None
    round: Round | None = None
    section_number: int | None = None
    relay_legs: int | None = None
    distance: int | None = None
    stroke: Stroke | None = None
    exercise: Exercise | None = None
    gender: EventGender | None = None
    best_list_category: BestListCategory | None = None
    qualification_event_number: int | None = None
    qualification_round: Round | None = None


class AgeGroup(DsvElement):
    """``WERTUNG`` — one scoring group of an event."""

    event_number: int | None = None
    round: Round | None = None
    scoring_id: int | None = None
    class_type: AgeClassType | None = None
    lower_bound: str | None = None
    upper_bound: str | None = None
    gender: EventGender | None = None
    name: str | None = None


class QualificationTime(DsvElement):
    """``PFLICHTZEIT`` — the qualifying time for one event and age group."""

    event_number: int | None = None
    round: Round | None = None
    class_type: AgeClassType | None = None
    lower_bound: str | None = None
    upper_bound: str | None = None
    time_millis: int | None = None
    gender: Gender | None = None


class EntryFee(DsvElement):
    """``MELDEGELD`` — one fee position of the announcement."""

    fee_type: EntryFeeType | None = None
    amount_cents: int | None = None
    event_number: int | None = None


# --- Participants ---------------------------------------------------------


class Club(DsvElement):
    """``VEREIN`` — a participating club."""

    name: str | None = None
    dsv_club_id: int | None = None
    lsv_code: int | None = None
    nation: str | None = None
    direct_debit_approved: bool | None = None


class Coach(DsvElement):
    """``TRAINER`` — a coach nominated by a club."""

    number: int | None = None
    name: str | None = None
    gender: Gender | None = None


class Swimmer(DsvElement):
    """``PNMELDUNG`` (entry list, with coach) / ``PERSON`` (result list, without)."""

    name: str | None = None
    dsv_id: int | None = None
    local_id: int | None = None
    gender: Gender | None = None
    birth_year: int | None = None
    age_class: int | None = None
    coach_number: int | None = None
    nationality_1: str | None = None
    nationality_2: str | None = None
    nationality_3: str | None = None


class Handicap(DsvElement):
    """``HANDICAP`` — a para swimmer's classification."""

    swimmer_local_id: int | None = None
    dbs_id: str | None = None
    ipc_id: str | None = None
    start_class: str | None = None
    start_class_breast: str | None = None
    start_class_medley: str | None = None
    exceptions: str | None = None


class JudgeNomination(DsvElement):
    """``KARIMELDUNG`` — a judge a club brings to the meet."""

    number: int | None = None
    name: str | None = None
    group: JudgeGroup | None = None
    gender: Gender | None = None


class JudgeSectionWish(DsvElement):
    """``KARIABSCHNITT`` — which section a nominated judge is available for."""

    judge_number: int | None = None
    section_number: int | None = None
    position: JudgePosition | None = None


class JudgeAssignment(DsvElement):
    """``KAMPFGERICHT`` — a judge actually assigned in a result list."""

    section_number: int | None = None
    position: JudgePosition | None = None
    name: str | None = None
    club_name: str | None = None


# --- Entries --------------------------------------------------------------


class IndividualEntry(DsvElement):
    """``STARTPN`` — one swimmer's entry into one event."""

    swimmer_local_id: int | None = None
    event_number: int | None = None
    entry_time_millis: int | None = None


class Relay(DsvElement):
    """``STMELDUNG`` (entry list) / ``STAFFEL`` (result list) — a relay team."""

    team_number: int | None = None
    local_id: int | None = None
    class_type: AgeClassType | None = None
    lower_bound: str | None = None
    upper_bound: str | None = None
    name: str | None = None


class RelayEntry(DsvElement):
    """``STARTST`` — one relay team's entry into one event."""

    relay_local_id: int | None = None
    event_number: int | None = None
    entry_time_millis: int | None = None


class RelaySwimmer(DsvElement):
    """``STAFFELPERSON`` — one leg of a relay.

    The entry-list shape references the swimmer by its meet-local id; the
    result-list shape identifies the swimmer inline and carries the round.
    """

    relay_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    swimmer_local_id: int | None = None
    name: str | None = None
    dsv_id: int | None = None
    leg_number: int | None = None
    gender: Gender | None = None
    birth_year: int | None = None
    age_class: int | None = None
    nationality_1: str | None = None
    nationality_2: str | None = None
    nationality_3: str | None = None


# --- Results --------------------------------------------------------------


class IndividualResult(DsvElement):
    """``PERSONENERGEBNIS`` (club list) / ``PNERGEBNIS`` (meet protocol)."""

    swimmer_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    scoring_id: int | None = None
    place: int | None = None
    time_millis: int | None = None
    status: ResultStatus | None = None
    name: str | None = None
    dsv_id: int | None = None
    gender: Gender | None = None
    birth_year: int | None = None
    age_class: int | None = None
    club_name: str | None = None
    club_dsv_id: int | None = None
    remark: str | None = None
    enm: EnmStatus | None = None
    nationality_1: str | None = None
    nationality_2: str | None = None
    nationality_3: str | None = None


class Split(DsvElement):
    """``PNZWISCHENZEIT`` — one intermediate time of an individual swim."""

    swimmer_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    distance: int | None = None
    time_millis: int | None = None


class Reaction(DsvElement):
    """``PNREAKTION`` — the start reaction time of an individual swim."""

    swimmer_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    negative: bool | None = None
    time_millis: int | None = None


class RelayResult(DsvElement):
    """``STAFFELERGEBNIS`` (club list) / ``STERGEBNIS`` (meet protocol)."""

    relay_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    scoring_id: int | None = None
    place: int | None = None
    time_millis: int | None = None
    status: ResultStatus | None = None
    team_number: int | None = None
    club_name: str | None = None
    club_dsv_id: int | None = None
    disqualified_leg: int | None = None
    remark: str | None = None
    enm: EnmStatus | None = None


class RelaySplit(DsvElement):
    """``STZWISCHENZEIT`` — one intermediate time of a relay swim."""

    relay_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    leg_number: int | None = None
    distance: int | None = None
    time_millis: int | None = None


class RelayTakeoff(DsvElement):
    """``STABLOESE`` — one relay changeover time."""

    relay_local_id: int | None = None
    event_number: int | None = None
    round: Round | None = None
    leg_number: int | None = None
    negative: bool | None = None
    time_millis: int | None = None
