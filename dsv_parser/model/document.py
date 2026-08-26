"""The parsed document — one container for all four DSV list kinds.

Which blocks are populated depends on :attr:`DsvDocument.file_type`; a definition
list has events and fees and no results, a meet protocol the other way round. One
container rather than four subclasses is a deliberate trade: consumers in other
languages get a single, stable JSON shape they can generate a client for once,
and the emptiness of a block is data rather than a type distinction.

Element lists preserve file order. For :attr:`DsvDocument.events` that order *is*
the meet programme and is semantically relevant; for the rest it is simply the
order the writer chose, and consumers should not rely on it.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from .elements import (
    AgeGroup,
    BankAccount,
    Club,
    Coach,
    Contact,
    EntryFee,
    Event,
    Generator,
    Handicap,
    Host,
    IndividualEntry,
    IndividualResult,
    JudgeAssignment,
    JudgeNomination,
    JudgeSectionWish,
    MeetInfo,
    ProofOfTime,
    QualificationTime,
    Reaction,
    Relay,
    RelayEntry,
    RelayResult,
    RelaySplit,
    RelaySwimmer,
    RelayTakeoff,
    Section,
    Split,
    Swimmer,
    Venue,
)
from .enums import FileType


class DsvDocument(BaseModel):
    """The complete, lossless in-memory representation of one DSV file."""

    model_config = ConfigDict(extra="forbid")

    # --- header ---
    file_type: FileType | None = Field(default=None, description="Listart of the FORMAT element.")
    version: int | None = Field(
        default=None, description="DSV format version (5, 6, 7 or 8) as declared by FORMAT."
    )
    generator: Generator | None = Field(default=None, description="ERZEUGER.")
    meet: MeetInfo | None = Field(default=None, description="VERANSTALTUNG.")
    venue: Venue | None = Field(default=None, description="VERANSTALTUNGSORT.")
    announcement_url: str | None = Field(default=None, description="AUSSCHREIBUNGIMNETZ.")
    organizer_name: str | None = Field(default=None, description="VERANSTALTER.")
    host: Host | None = Field(default=None, description="AUSRICHTER.")
    entry_address: Contact | None = Field(default=None, description="MELDEADRESSE.")
    contact_person: Contact | None = Field(default=None, description="ANSPRECHPARTNER.")
    entry_deadline: dt.datetime | None = Field(
        default=None, description="MELDESCHLUSS — date and clock merged into one instant."
    )
    bank_account: BankAccount | None = Field(default=None, description="BANKVERBINDUNG.")
    direct_debit_only: bool | None = Field(
        default=None, description="LASTSCHRIFT (Format 8); None means the element was absent."
    )
    remarks: str | None = Field(default=None, description="BESONDERES.")
    proof_of_time: ProofOfTime | None = Field(default=None, description="NACHWEIS.")

    # --- programme ---
    sections: list[Section] = Field(default_factory=list, description="ABSCHNITT.")
    events: list[Event] = Field(default_factory=list, description="WETTKAMPF, in programme order.")
    age_groups: list[AgeGroup] = Field(default_factory=list, description="WERTUNG.")
    qualification_times: list[QualificationTime] = Field(
        default_factory=list, description="PFLICHTZEIT."
    )
    entry_fees: list[EntryFee] = Field(default_factory=list, description="MELDEGELD.")

    # --- participants ---
    clubs: list[Club] = Field(default_factory=list, description="VEREIN.")
    coaches: list[Coach] = Field(default_factory=list, description="TRAINER.")
    swimmers: list[Swimmer] = Field(default_factory=list, description="PNMELDUNG / PERSON.")
    handicaps: list[Handicap] = Field(default_factory=list, description="HANDICAP.")
    judge_nominations: list[JudgeNomination] = Field(
        default_factory=list, description="KARIMELDUNG."
    )
    judge_section_wishes: list[JudgeSectionWish] = Field(
        default_factory=list, description="KARIABSCHNITT."
    )
    judge_assignments: list[JudgeAssignment] = Field(
        default_factory=list, description="KAMPFGERICHT."
    )

    # --- entries ---
    individual_entries: list[IndividualEntry] = Field(default_factory=list, description="STARTPN.")
    relays: list[Relay] = Field(default_factory=list, description="STMELDUNG / STAFFEL.")
    relay_entries: list[RelayEntry] = Field(default_factory=list, description="STARTST.")
    relay_swimmers: list[RelaySwimmer] = Field(default_factory=list, description="STAFFELPERSON.")

    # --- results ---
    individual_results: list[IndividualResult] = Field(
        default_factory=list, description="PERSONENERGEBNIS / PNERGEBNIS."
    )
    splits: list[Split] = Field(default_factory=list, description="PNZWISCHENZEIT.")
    reactions: list[Reaction] = Field(default_factory=list, description="PNREAKTION.")
    relay_results: list[RelayResult] = Field(
        default_factory=list, description="STAFFELERGEBNIS / STERGEBNIS."
    )
    relay_splits: list[RelaySplit] = Field(default_factory=list, description="STZWISCHENZEIT.")
    relay_takeoffs: list[RelayTakeoff] = Field(default_factory=list, description="STABLOESE.")

    def element_counts(self) -> dict[str, int]:
        """Summarise how many of each repeated element the document holds.

        Useful as a cheap smoke check after an import and as the payload of the
        CLI's ``--summary`` output.

        Returns:
            A mapping of field name to element count, skipping empty blocks.
        """
        counts: dict[str, int] = {}
        for name, value in self:
            if isinstance(value, list) and value:
                counts[name] = len(value)
        return counts
