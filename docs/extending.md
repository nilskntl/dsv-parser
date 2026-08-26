# Extending

Almost every change to the format is a change to one table. This page covers the
four cases that come up.

## Adding an element

Say a future format adds `SPONSOR: Name;Betrag;`.

**1. Add the model** in `model/elements.py`:

```python
class Sponsor(DsvElement):
    """``SPONSOR`` — a sponsor of the meet."""

    name: str | None = None
    amount_cents: int | None = None
```

**2. Add the document field** in `model/document.py`:

```python
sponsors: list[Sponsor] = Field(default_factory=list, description="SPONSOR.")
```

**3. Add the table entry** in `spec/elements.py`:

```python
(
    ElementSpec(
        element="SPONSOR",
        target="sponsors",
        model=el.Sponsor,
        versions=V9,
        file_types=DEFINITION,
        description="A sponsor of the meet.",
        attributes=(
            A("name", Kind.TEXT, "Sponsorname"),
            A("amount_cents", Kind.AMOUNT, "Betrag"),
        ),
    ),
)
```

Nothing else changes. The binder, the CLI, the API and the generated spec output
pick it up. `tests/unit/test_spec.py` checks that the field names line up.

## Adding a version delta

An attribute added in a later version gets a `versions=` marker. Position matters:
an attribute in the middle shifts everything after it, which is exactly what the
marker expresses.

```python
(A("account_holder", Kind.TEXT, "Kontoinhaber", versions=V8),)
```

An attribute that exists only in some list kinds works the same way:

```python
(A("direct_debit_approved", Kind.FLAG, "Lastschrift", versions=V8, file_types=CLUB_ENTRIES),)
```

A whole element gets the marker on the `ElementSpec` instead. The shorthands are
declared at the top of `spec/elements.py`: `V8`, `V7_PLUS`, `V6_PLUS`.

Add a test in `tests/unit/test_spec.py` asserting the attribute count per version:

```python
def test_bankverbindung_gains_kontoinhaber_in_format_8() -> None:
    spec = REGISTRY.lookup("BANKVERBINDUNG", 7, FileType.DEFINITION)
    assert len(spec.active(7, FileType.DEFINITION)) == 3
    assert len(spec.active(8, FileType.DEFINITION)) == 4
```

## Adding a variant layout

When an element has two genuinely different shapes rather than one shape with
optional attributes, declare it twice. Order matters: `Registry.lookup` returns
the first applicable entry, so the specific variant goes first.

```python
(ElementSpec(element="STAFFELPERSON", file_types=CLUB_ENTRIES, attributes=(...)),)
(ElementSpec(element="STAFFELPERSON", attributes=(...)),)  # everything else
```

## Adding a code

Vocabularies live in `model/enums.py`. A member is `NAME = ("speaking_value",
"CODE")`; put the version it appeared in into the docstring, since the enum itself
is not version-scoped.

```python
class Exercise(DsvEnum):
    KICKS_PRONE = ("kicks_prone", "KB")
    """Kicks Bauchlage — Format 8 onwards, and only with ``Technik = S``."""
```

Keeping the enum a superset across versions is deliberate: an older file never
contains the newer code, and a file that does contain it can be read.

Removed codes stay too, so that older files keep parsing. `BestListCategory.
OPEN_WATER` (`FS`) is the example; Format 7 dropped it.

## Supporting a new format version

1. Add the number to `VERSIONS` in `spec/fields.py`.
2. Add the shorthand (`V9 = frozenset({9})`) in `spec/elements.py`.
3. Work through the change log of the new specification and mark each entry.
4. Note the source document in the module docstring of `spec/elements.py`.
5. Add a fixture under `tests/fixtures/` and a test per structural change.

The parser accepts an unknown version already: it warns, then reads with the
newest known layout.

## Checking the result

```bash
make test          # includes the table invariants
make spec          # eyeball the rendered table
dsv-parser check real-file.DSV8
```

`check` against real files is the useful last step. A layout this table does not
model shows up as "attribute(s) beyond the N this layout declares".
