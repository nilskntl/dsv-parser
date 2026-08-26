"""The element table — the single source of truth for every DSV layout.

Read this file as the specification itself: one :class:`~dsv_parser.spec.fields.ElementSpec`
per element, attributes in the order the file writes them, with ``versions=`` and
``file_types=`` marking every place the formats disagree. Nothing else in the
package knows the attribute order of anything.

Provenance
----------
The table is transcribed from the two official DSV documents:

* *„DSV Standard“ — Standardisierung des Datenaustausches*, **Format 6**,
  1 November 2015, in force 1 September 2015.
* *ebenda*, **Format 7**, 31 August 2022, in force 1 January 2023.
* *ebenda*, **Format 8**, 14 March 2026, in force 1 August 2026; Format 7 stays
  valid until 31 December 2026.

Every ``versions=`` marker is one line of one of those documents' change logs:
``V8`` from the Format 8 log, ``V7_PLUS`` from the Format 7 log against Format 6,
``V6_PLUS`` from the Format 6 log. The layouts were additionally checked against
real EasyWk output in Format 6 and Format 7.

Coverage by format version
--------------------------
**Format 7 and 8** are complete: all four Listarten, every element, every
attribute, with the six Format 8 deltas marked —

1. ``BANKVERBINDUNG`` gains ``Kontoinhaber``.
2. ``LASTSCHRIFT`` is a new element in the Wettkampfdefinitionsliste.
3. ``VEREIN`` gains a ``Lastschrift`` flag, in the Vereinsmeldeliste only.
4. ``TRAINER`` gains ``Geschlecht``.
5. ``KARIMELDUNG`` gains ``Geschlecht``.
6. ``MELDEGELD`` gains the types *Teilnehmermeldegeld* and *Abschnittspauschale*;
   ``Ausübung`` gains ``KB``/``KR`` (Kicks Bauch-/Rückenlage). Both are vocabulary
   additions, marked in :mod:`dsv_parser.model.enums` rather than here.

The Format 8 ZIP variant (``.DSV8z``) is handled in
:mod:`dsv_parser.core.decoding`.

**Format 6** is Format 7 minus the Format 7 change log, of which two entries move
attribute positions and are therefore modelled here: the three ``Nationalität``
attributes do not exist (verified against real Format 6 protocols — ``PNERGEBNIS``
carries 16 attributes there against 19 in Format 7), and ``HANDICAP`` does not
exist. The rest of that change log is vocabulary: ``EW``/``PA`` best-list
categories and the gender ``D`` arrive in Format 7, the Freiwasser best-list code
``FS`` leaves with it, and six judge positions are added — all marked in
:mod:`dsv_parser.model.enums`.

**Format 5** is Format 6 minus the Format 6 change log, whose four structural
entries are modelled here: ``ABSCHNITT`` has no ``Relative Angabe`` attribute, and
the elements ``NACHWEIS``, ``PNREAKTION`` and ``STABLOESE`` do not exist. One
Format 5 idiom has no representation and is called out by
:mod:`dsv_parser.core.parser`: a reaction time was carried as a
``PNZWISCHENZEIT`` with ``Distanz = 0``, which Format 6 replaced with
``PNREAKTION``. See ``TODO(spec-v5)`` below for the residual uncertainty.
"""

from __future__ import annotations

from ..model import elements as el
from ..model.enums import (
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
from .fields import Attribute as A
from .fields import ElementSpec, Kind, Registry

# --- shorthand for the applicability markers ------------------------------

V8 = frozenset({8})
#: Attributes and elements the Format 7 change log introduced against Format 6.
V7_PLUS = frozenset({7, 8})
#: Attributes and elements the Format 6 change log introduced — absent from Format 5.
V6_PLUS = frozenset({6, 7, 8})
DEFINITION = frozenset({FileType.DEFINITION})
CLUB_ENTRIES = frozenset({FileType.CLUB_ENTRIES})
CLUB_RESULTS = frozenset({FileType.CLUB_RESULTS})
MEET_RESULTS = frozenset({FileType.MEET_RESULTS})
RESULT_LISTS = CLUB_RESULTS | MEET_RESULTS
#: Every list kind except the Vereinsmeldeliste — the one that omits the
#: Bestenliste attribute of ``WETTKAMPF`` and thereby shifts the two
#: qualification attributes one position forward.
WITH_BEST_LIST = DEFINITION | RESULT_LISTS

# A postal contact block, shared verbatim by MELDEADRESSE and ANSPRECHPARTNER.
_CONTACT = (
    A("name", Kind.TEXT, "Name"),
    A("street", Kind.TEXT, "Strasse"),
    A("postal_code", Kind.TEXT, "PLZ"),
    A("city", Kind.TEXT, "Ort"),
    A("nation", Kind.TEXT, "Land"),
    A("phone", Kind.TEXT, "Telefon"),
    A("fax", Kind.TEXT, "Fax"),
    A("email", Kind.TEXT, "eMail"),
)

# The inline swimmer identity repeated by the result-list element shapes.
# Introduced by Format 7 ("Einführung der Nationalität bei Meldungen und
# Ergebnissen"). They sit at the end of every element that carries them, so in a
# Format 6 file the element is simply three attributes shorter.
_NATIONALITIES = (
    A("nationality_1", Kind.TEXT, "Nationalität 1", versions=V7_PLUS),
    A("nationality_2", Kind.TEXT, "Nationalität 2", versions=V7_PLUS),
    A("nationality_3", Kind.TEXT, "Nationalität 3", versions=V7_PLUS),
)


ELEMENTS: tuple[ElementSpec, ...] = (
    # === File header =====================================================
    ElementSpec(
        element="FORMAT",
        target=None,
        model=el.Format,
        repeated=False,
        description="Mandatory first line: list kind and format version.",
        attributes=(
            A("file_type", Kind.ENUM, "Listart", enum=FileType),
            A("version", Kind.INT, "Version"),
        ),
    ),
    ElementSpec(
        element="ERZEUGER",
        target="generator",
        model=el.Generator,
        repeated=False,
        description="The software that wrote the file.",
        attributes=(
            A("software", Kind.TEXT, "Software"),
            A("version", Kind.TEXT, "Version"),
            A("contact", Kind.TEXT, "Kontakt"),
        ),
    ),
    ElementSpec(
        element="VERANSTALTUNG",
        target="meet",
        model=el.MeetInfo,
        repeated=False,
        description="Meet name, city, pool length and timing system.",
        attributes=(
            A("name", Kind.TEXT, "Veranstaltungsbezeichnung"),
            A("city", Kind.TEXT, "Veranstaltungsort"),
            A("course", Kind.ENUM, "Bahnlänge", enum=Course),
            A("timing", Kind.ENUM, "Zeitmessung", enum=TimingSystem),
        ),
    ),
    ElementSpec(
        element="VERANSTALTUNGSORT",
        target="venue",
        model=el.Venue,
        repeated=False,
        file_types=DEFINITION,
        description="The pool and how to reach it.",
        attributes=(
            A("name", Kind.TEXT, "Bezeichnung"),
            A("street", Kind.TEXT, "Strasse"),
            A("postal_code", Kind.TEXT, "PLZ"),
            A("city", Kind.TEXT, "Ort"),
            A("nation", Kind.TEXT, "Land"),
            A("phone", Kind.TEXT, "Telefon"),
            A("fax", Kind.TEXT, "Fax"),
            A("email", Kind.TEXT, "eMail"),
        ),
    ),
    ElementSpec(
        element="AUSSCHREIBUNGIMNETZ",
        target="announcement_url",
        model=el.ScalarText,
        unwrap="value",
        repeated=False,
        file_types=DEFINITION,
        description="URL of the online announcement.",
        attributes=(A("value", Kind.TEXT, "Internetadresse"),),
    ),
    ElementSpec(
        element="VERANSTALTER",
        target="organizer_name",
        model=el.ScalarText,
        unwrap="value",
        repeated=False,
        file_types=DEFINITION | RESULT_LISTS,
        description="The association or club staging the meet.",
        attributes=(A("value", Kind.TEXT, "Name"),),
    ),
    ElementSpec(
        element="BESONDERES",
        target="remarks",
        model=el.ScalarText,
        unwrap="value",
        repeated=False,
        file_types=DEFINITION,
        description="Free-text remarks of the announcement.",
        attributes=(A("value", Kind.TEXT, "Bemerkungen"),),
    ),
    ElementSpec(
        element="LASTSCHRIFT",
        target="direct_debit_only",
        model=el.ScalarFlag,
        unwrap="value",
        repeated=False,
        versions=V8,
        file_types=DEFINITION,
        description="Whether entry fees are collected by direct debit only.",
        attributes=(A("value", Kind.FLAG, "Nur Lastschrift"),),
    ),
    ElementSpec(
        element="MELDESCHLUSS",
        target="entry_deadline",
        model=el.EntryDeadline,
        repeated=False,
        file_types=DEFINITION,
        description="Entry deadline; the assembler merges date and clock into one instant.",
        attributes=(
            A("date", Kind.DATE, "Meldeschluss Datum"),
            A("time", Kind.CLOCK, "Meldeschluss Uhrzeit"),
        ),
    ),
    ElementSpec(
        element="AUSRICHTER",
        target="host",
        model=el.Host,
        repeated=False,
        file_types=DEFINITION | RESULT_LISTS,
        description="The organising club and its contact person.",
        attributes=(
            A("name", Kind.TEXT, "Name"),
            A("contact_name", Kind.TEXT, "Kontakt"),
            A("street", Kind.TEXT, "Strasse"),
            A("postal_code", Kind.TEXT, "PLZ"),
            A("city", Kind.TEXT, "Ort"),
            A("nation", Kind.TEXT, "Land"),
            A("phone", Kind.TEXT, "Telefon"),
            A("fax", Kind.TEXT, "Fax"),
            A("email", Kind.TEXT, "eMail"),
        ),
    ),
    ElementSpec(
        element="MELDEADRESSE",
        target="entry_address",
        model=el.Contact,
        repeated=False,
        file_types=DEFINITION,
        description="Where entries are sent.",
        attributes=_CONTACT,
    ),
    ElementSpec(
        element="ANSPRECHPARTNER",
        target="contact_person",
        model=el.Contact,
        repeated=False,
        file_types=CLUB_ENTRIES,
        description="The entering club's contact person.",
        attributes=_CONTACT,
    ),
    ElementSpec(
        element="BANKVERBINDUNG",
        target="bank_account",
        model=el.BankAccount,
        repeated=False,
        file_types=DEFINITION,
        description="Where entry fees are paid.",
        attributes=(
            A("bank_name", Kind.TEXT, "Bankname"),
            A("iban", Kind.TEXT, "IBAN"),
            A("bic", Kind.TEXT, "BIC"),
            A("account_holder", Kind.TEXT, "Kontoinhaber", versions=V8),
        ),
    ),
    ElementSpec(
        element="NACHWEIS",
        target="proof_of_time",
        model=el.ProofOfTime,
        repeated=False,
        versions=V6_PLUS,
        file_types=DEFINITION,
        description="Window and course a qualifying time may be proven on.",
        attributes=(
            A("valid_from", Kind.DATE, "Nachweis von"),
            A("valid_until", Kind.DATE, "Nachweis bis"),
            A("course", Kind.ENUM, "Bahnlänge", enum=ProofCourse),
        ),
    ),
    # === Programme =======================================================
    ElementSpec(
        element="ABSCHNITT",
        target="sections",
        model=el.Section,
        description=(
            "One session. The definition list additionally carries the admission "
            "and judges'-briefing times, which shift the start time two positions."
        ),
        attributes=(
            A("number", Kind.INT, "Abschnittsnummer"),
            A("date", Kind.DATE, "Abschnittsdatum"),
            A("admission_time", Kind.CLOCK, "Einlass", file_types=DEFINITION),
            A(
                "judges_meeting_time",
                Kind.CLOCK,
                "Kampfrichtersitzung",
                file_types=DEFINITION,
            ),
            A("start_time", Kind.CLOCK, "Anfangszeit"),
            A("relative_timing", Kind.FLAG, "Relative Angabe", versions=V6_PLUS),
        ),
    ),
    ElementSpec(
        element="WETTKAMPF",
        target="events",
        model=el.Event,
        description=(
            "One event of the programme. The Vereinsmeldeliste omits the "
            "Bestenliste attribute, shifting both qualification attributes forward."
        ),
        attributes=(
            A("number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("section_number", Kind.INT, "Abschnittsnummer"),
            A("relay_legs", Kind.INT, "Anzahl Starter"),
            A("distance", Kind.INT, "Einzelstrecke"),
            A("stroke", Kind.ENUM, "Technik", enum=Stroke),
            A("exercise", Kind.ENUM, "Ausübung", enum=Exercise),
            A("gender", Kind.ENUM, "Geschlecht", enum=EventGender),
            A(
                "best_list_category",
                Kind.ENUM,
                "Zuordnung Bestenliste",
                enum=BestListCategory,
                file_types=WITH_BEST_LIST,
            ),
            A("qualification_event_number", Kind.INT, "Qualifikationswettkampf"),
            A("qualification_round", Kind.ENUM, "Qualifikationswettkampfart", enum=Round),
        ),
    ),
    ElementSpec(
        element="WERTUNG",
        target="age_groups",
        model=el.AgeGroup,
        file_types=DEFINITION | RESULT_LISTS,
        description="One scoring group of an event.",
        attributes=(
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("scoring_id", Kind.INT, "Wertungs-ID"),
            A("class_type", Kind.ENUM, "Wertungsklasse", enum=AgeClassType),
            A("lower_bound", Kind.TEXT, "Mindest-JG/AK"),
            A("upper_bound", Kind.TEXT, "Höchst-JG/AK"),
            A("gender", Kind.ENUM, "Geschlecht", enum=EventGender),
            A("name", Kind.TEXT, "Wertungsname"),
        ),
    ),
    ElementSpec(
        element="PFLICHTZEIT",
        target="qualification_times",
        model=el.QualificationTime,
        file_types=DEFINITION,
        description="The qualifying time for one event and age group.",
        attributes=(
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("class_type", Kind.ENUM, "Wertungsklasse", enum=AgeClassType),
            A("lower_bound", Kind.TEXT, "Mindest-JG/AK"),
            A("upper_bound", Kind.TEXT, "Höchst-JG/AK"),
            A("time_millis", Kind.SWIM_TIME, "Pflichtzeit"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender),
        ),
    ),
    ElementSpec(
        element="MELDEGELD",
        target="entry_fees",
        model=el.EntryFee,
        file_types=DEFINITION,
        description="One fee position of the announcement.",
        attributes=(
            A("fee_type", Kind.ENUM, "Meldegeldtyp", enum=EntryFeeType),
            A("amount_cents", Kind.AMOUNT, "Betrag"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
        ),
    ),
    # === Participants ====================================================
    ElementSpec(
        element="VEREIN",
        target="clubs",
        model=el.Club,
        file_types=CLUB_ENTRIES | RESULT_LISTS,
        description="A participating club.",
        attributes=(
            A("name", Kind.TEXT, "Vereinsbezeichnung"),
            A("dsv_club_id", Kind.INT, "Vereinskennzahl"),
            A("lsv_code", Kind.INT, "Landesschwimmverband"),
            A("nation", Kind.TEXT, "Nation"),
            A(
                "direct_debit_approved",
                Kind.FLAG,
                "Lastschrift",
                versions=V8,
                file_types=CLUB_ENTRIES,
            ),
        ),
    ),
    ElementSpec(
        element="TRAINER",
        target="coaches",
        model=el.Coach,
        file_types=CLUB_ENTRIES,
        description="A coach nominated by the entering club.",
        attributes=(
            A("number", Kind.INT, "Trainernummer"),
            A("name", Kind.TEXT, "Trainername"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender, versions=V8),
        ),
    ),
    ElementSpec(
        element="PNMELDUNG",
        target="swimmers",
        model=el.Swimmer,
        file_types=CLUB_ENTRIES,
        description="A swimmer in an entry list — carries the coach reference.",
        attributes=(
            A("name", Kind.TEXT, "Name"),
            A("dsv_id", Kind.INT, "DSV-ID"),
            A("local_id", Kind.INT, "Veranstaltungs-ID"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender),
            A("birth_year", Kind.INT, "Jahrgang"),
            A("age_class", Kind.INT, "Altersklasse"),
            A("coach_number", Kind.INT, "Trainernummer"),
            *_NATIONALITIES,
        ),
    ),
    ElementSpec(
        element="PERSON",
        target="swimmers",
        model=el.Swimmer,
        file_types=CLUB_RESULTS,
        description="A swimmer in a club result list — no coach reference.",
        attributes=(
            A("name", Kind.TEXT, "Name"),
            A("dsv_id", Kind.INT, "DSV-ID"),
            A("local_id", Kind.INT, "Veranstaltungs-ID"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender),
            A("birth_year", Kind.INT, "Jahrgang"),
            A("age_class", Kind.INT, "Altersklasse"),
            *_NATIONALITIES,
        ),
    ),
    ElementSpec(
        element="HANDICAP",
        target="handicaps",
        model=el.Handicap,
        versions=V7_PLUS,
        file_types=CLUB_ENTRIES,
        description="A para swimmer's classification.",
        attributes=(
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("dbs_id", Kind.TEXT, "DBS-ID"),
            A("ipc_id", Kind.TEXT, "IPC-ID"),
            A("start_class", Kind.TEXT, "Startklasse"),
            A("start_class_breast", Kind.TEXT, "Startklasse Brust"),
            A("start_class_medley", Kind.TEXT, "Startklasse Lagen"),
            A("exceptions", Kind.TEXT, "Ausnahmegenehmigungen"),
        ),
    ),
    ElementSpec(
        element="KARIMELDUNG",
        target="judge_nominations",
        model=el.JudgeNomination,
        file_types=CLUB_ENTRIES,
        description="A judge the entering club brings to the meet.",
        attributes=(
            A("number", Kind.INT, "Kampfrichternummer"),
            A("name", Kind.TEXT, "Kampfrichtername"),
            A("group", Kind.ENUM, "Kampfrichtergruppe", enum=JudgeGroup),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender, versions=V8),
        ),
    ),
    ElementSpec(
        element="KARIABSCHNITT",
        target="judge_section_wishes",
        model=el.JudgeSectionWish,
        file_types=CLUB_ENTRIES,
        description="Which section a nominated judge is available for.",
        attributes=(
            A("judge_number", Kind.INT, "Kampfrichternummer"),
            A("section_number", Kind.INT, "Abschnittsnummer"),
            A("position", Kind.ENUM, "Einsatzwunsch", enum=JudgePosition),
        ),
    ),
    ElementSpec(
        element="KAMPFGERICHT",
        target="judge_assignments",
        model=el.JudgeAssignment,
        file_types=RESULT_LISTS,
        description="A judge actually assigned to a section.",
        attributes=(
            A("section_number", Kind.INT, "Abschnittsnummer"),
            A("position", Kind.ENUM, "Kampfrichteraufgabe", enum=JudgePosition),
            A("name", Kind.TEXT, "Name"),
            A("club_name", Kind.TEXT, "Verein"),
        ),
    ),
    # === Entries =========================================================
    ElementSpec(
        element="STARTPN",
        target="individual_entries",
        model=el.IndividualEntry,
        file_types=CLUB_ENTRIES,
        description="One swimmer's entry into one event.",
        attributes=(
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("entry_time_millis", Kind.SWIM_TIME, "Meldezeit"),
        ),
    ),
    ElementSpec(
        element="STMELDUNG",
        target="relays",
        model=el.Relay,
        file_types=CLUB_ENTRIES,
        description="A relay team in an entry list.",
        attributes=(
            A("team_number", Kind.INT, "Mannschaftsnummer"),
            A("local_id", Kind.INT, "Veranstaltungs-ID"),
            A("class_type", Kind.ENUM, "Wertungsklasse", enum=AgeClassType),
            A("lower_bound", Kind.TEXT, "Mindest-JG/AK"),
            A("upper_bound", Kind.TEXT, "Höchst-JG/AK"),
            A("name", Kind.TEXT, "Staffelname"),
        ),
    ),
    ElementSpec(
        element="STAFFEL",
        target="relays",
        model=el.Relay,
        file_types=CLUB_RESULTS,
        description=(
            "A relay team in a club result list. The Wettkampfergebnisliste has no "
            "STAFFEL element — STERGEBNIS identifies the team inline."
        ),
        attributes=(
            A("team_number", Kind.INT, "Mannschaftsnummer"),
            A("local_id", Kind.INT, "Veranstaltungs-ID"),
            A("class_type", Kind.ENUM, "Wertungsklasse", enum=AgeClassType),
            A("lower_bound", Kind.TEXT, "Mindest-JG/AK"),
            A("upper_bound", Kind.TEXT, "Höchst-JG/AK"),
        ),
    ),
    ElementSpec(
        element="STARTST",
        target="relay_entries",
        model=el.RelayEntry,
        file_types=CLUB_ENTRIES,
        description="One relay team's entry into one event.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("entry_time_millis", Kind.SWIM_TIME, "Meldezeit"),
        ),
    ),
    # Two shapes, specific first: the entry list references the swimmer by its
    # meet-local id, the result lists identify the swimmer inline.
    ElementSpec(
        element="STAFFELPERSON",
        target="relay_swimmers",
        model=el.RelaySwimmer,
        file_types=CLUB_ENTRIES,
        description="One leg of a relay, referencing an already-declared swimmer.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID Staffel"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID Person"),
            A("leg_number", Kind.INT, "Startfolge"),
        ),
    ),
    ElementSpec(
        element="STAFFELPERSON",
        target="relay_swimmers",
        model=el.RelaySwimmer,
        file_types=RESULT_LISTS,
        description="One leg of a relay, with the swimmer identified inline.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID Staffel"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("name", Kind.TEXT, "Name"),
            A("dsv_id", Kind.INT, "DSV-ID"),
            A("leg_number", Kind.INT, "Startfolge"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender),
            A("birth_year", Kind.INT, "Jahrgang"),
            A("age_class", Kind.INT, "Altersklasse"),
            *_NATIONALITIES,
        ),
    ),
    # === Results =========================================================
    ElementSpec(
        element="PERSONENERGEBNIS",
        target="individual_results",
        model=el.IndividualResult,
        file_types=CLUB_RESULTS,
        description="An individual result in a club result list.",
        attributes=(
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("scoring_id", Kind.INT, "Wertungs-ID"),
            A("place", Kind.INT, "Platz"),
            A("time_millis", Kind.SWIM_TIME, "Endzeit"),
            A("status", Kind.ENUM, "Grund der Nichtwertung", enum=ResultStatus),
            A("remark", Kind.TEXT, "Bemerkung"),
            A("enm", Kind.ENUM, "ENM", enum=EnmStatus),
        ),
    ),
    ElementSpec(
        element="PNERGEBNIS",
        target="individual_results",
        model=el.IndividualResult,
        file_types=MEET_RESULTS,
        description="An individual result in the meet protocol, swimmer identified inline.",
        attributes=(
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("scoring_id", Kind.INT, "Wertungs-ID"),
            A("place", Kind.INT, "Platz"),
            A("status", Kind.ENUM, "Grund der Nichtwertung", enum=ResultStatus),
            A("name", Kind.TEXT, "Name"),
            A("dsv_id", Kind.INT, "DSV-ID"),
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("gender", Kind.ENUM, "Geschlecht", enum=Gender),
            A("birth_year", Kind.INT, "Jahrgang"),
            A("age_class", Kind.INT, "Altersklasse"),
            A("club_name", Kind.TEXT, "Vereinsbezeichnung"),
            A("club_dsv_id", Kind.INT, "Vereinskennzahl"),
            A("time_millis", Kind.SWIM_TIME, "Endzeit"),
            A("remark", Kind.TEXT, "Bemerkung"),
            A("enm", Kind.ENUM, "ENM", enum=EnmStatus),
            *_NATIONALITIES,
        ),
    ),
    ElementSpec(
        element="PNZWISCHENZEIT",
        target="splits",
        model=el.Split,
        file_types=RESULT_LISTS,
        description="One intermediate time of an individual swim.",
        attributes=(
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("distance", Kind.INT, "Zwischenzeitdistanz"),
            A("time_millis", Kind.SWIM_TIME, "Zwischenzeit"),
        ),
    ),
    ElementSpec(
        element="PNREAKTION",
        target="reactions",
        model=el.Reaction,
        versions=V6_PLUS,
        file_types=RESULT_LISTS,
        description="The start reaction time of an individual swim.",
        attributes=(
            A("swimmer_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("negative", Kind.SIGN, "Vorzeichen"),
            A("time_millis", Kind.SWIM_TIME, "Reaktionszeit"),
        ),
    ),
    ElementSpec(
        element="STAFFELERGEBNIS",
        target="relay_results",
        model=el.RelayResult,
        file_types=CLUB_RESULTS,
        description="A relay result in a club result list.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("scoring_id", Kind.INT, "Wertungs-ID"),
            A("place", Kind.INT, "Platz"),
            A("time_millis", Kind.SWIM_TIME, "Endzeit"),
            A("status", Kind.ENUM, "Grund der Nichtwertung", enum=ResultStatus),
            A("disqualified_leg", Kind.INT, "Startfolge DS"),
            A("remark", Kind.TEXT, "Bemerkung"),
            A("enm", Kind.ENUM, "ENM", enum=EnmStatus),
        ),
    ),
    ElementSpec(
        element="STERGEBNIS",
        target="relay_results",
        model=el.RelayResult,
        file_types=MEET_RESULTS,
        description="A relay result in the meet protocol, club identified inline.",
        attributes=(
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("scoring_id", Kind.INT, "Wertungs-ID"),
            A("place", Kind.INT, "Platz"),
            A("status", Kind.ENUM, "Grund der Nichtwertung", enum=ResultStatus),
            A("team_number", Kind.INT, "Mannschaftsnummer"),
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("club_name", Kind.TEXT, "Vereinsbezeichnung"),
            A("club_dsv_id", Kind.INT, "Vereinskennzahl"),
            A("time_millis", Kind.SWIM_TIME, "Endzeit"),
            A("disqualified_leg", Kind.INT, "Startfolge DS"),
            A("remark", Kind.TEXT, "Bemerkung"),
            A("enm", Kind.ENUM, "ENM", enum=EnmStatus),
        ),
    ),
    ElementSpec(
        element="STZWISCHENZEIT",
        target="relay_splits",
        model=el.RelaySplit,
        file_types=RESULT_LISTS,
        description="One intermediate time of a relay swim.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("leg_number", Kind.INT, "Startfolge"),
            A("distance", Kind.INT, "Zwischenzeitdistanz"),
            A("time_millis", Kind.SWIM_TIME, "Zwischenzeit"),
        ),
    ),
    ElementSpec(
        element="STABLOESE",
        target="relay_takeoffs",
        model=el.RelayTakeoff,
        versions=V6_PLUS,
        file_types=RESULT_LISTS,
        description="One relay changeover time.",
        attributes=(
            A("relay_local_id", Kind.INT, "Veranstaltungs-ID"),
            A("event_number", Kind.INT, "Wettkampfnummer"),
            A("round", Kind.ENUM, "Wettkampfart", enum=Round),
            A("leg_number", Kind.INT, "Startfolge"),
            A("negative", Kind.SIGN, "Vorzeichen"),
            A("time_millis", Kind.SWIM_TIME, "Ablösezeit"),
        ),
    ),
)

#: Elements the assembler post-processes because they do not map onto a document
#: field one-to-one: ``FORMAT`` steers the whole parse (its two attributes become
#: two document fields) and ``MELDESCHLUSS`` merges a date and a clock into one
#: instant. ``DATEIENDE`` carries no attributes and is handled by the parser loop.
POST_PROCESSED: frozenset[str] = frozenset({"FORMAT", "MELDESCHLUSS"})

# TODO(spec-v5): the Format 5 deltas above are derived from the Format 6 change log,
# not from the Format 5 document itself — the DSV no longer publishes it. The log is
# dated after the "Format 6, März 2015" release, so strictly it records amendments to
# Format 6; a Format 5 file predates all of them either way, but a Format 6 file written
# between March and October 2015 will also lack them (harmlessly: the missing attribute
# is the last one of its element, and a missing element is simply absent). Confirm
# against a copy of the Format 5 document or against real Format 5 files, then drop the
# residual warning in `dsv_parser.core.parser`.

REGISTRY = Registry(ELEMENTS)
