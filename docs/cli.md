# CLI

Installed as `dsv-parser`, and runnable as `python -m dsv_parser`. Every
subcommand takes one file, or `-` to read from stdin.

## `parse` — file to JSON

```bash
dsv-parser parse meet.DSV8                 # indented JSON on stdout
dsv-parser parse meet.DSV8 -o meet.json    # …or to a file
cat meet.DSV8 | dsv-parser parse -         # …or from a pipe
```

| Flag | Effect |
| --- | --- |
| `-o, --output PATH` | Write to a file instead of stdout |
| `--compact` | Single-line JSON |
| `--exclude-none` | Drop null fields — far smaller, variable shape |
| `--diagnostics` | Wrap document and diagnostics in one envelope |
| `--summary` | Header and element counts only, no document |
| `-q, --quiet` | Do not print diagnostics to stderr |
| `--strict` | Exit 1 when any data was lost |

Diagnostics go to stderr and the document to stdout, so
`dsv-parser parse meet.DSV8 > meet.json` writes clean JSON and still shows the
problems.

## `check` — validate

```bash
dsv-parser check meet.DSV8
```

```
warning: line 1204 (VEREIN): 2 attribute(s) beyond the 4 this layout declares, ignored …
meet.DSV8: meet_results format 8, 9686 elements, 0 error(s), 1 warning(s)
```

Exit code 0 when nothing was lost, 1 otherwise. Intended for CI and batch
validation:

```bash
find . -iname '*.dsv*' -exec dsv-parser check {} \; | grep -v '0 error'
```

## `spec` — the element table

```bash
dsv-parser spec                  # plain text
dsv-parser spec --json           # machine-readable, same as GET /spec
dsv-parser spec -o SPEC.txt
```

Rendered from `spec/elements.py`, so it always matches the implementation.

```
WETTKAMPF
    One event of the programme. The Vereinsmeldeliste omits the Bestenliste …
     1. Wettkampfnummer               number                       int
     2. Wettkampfart                  round                        Round
     …
     9. Zuordnung Bestenliste         best_list_category           BestListCategory  (definition, club_results, meet_results)
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Data was lost (`check` always, `parse` with `--strict`) |
| 2 | No subcommand given |

An unreadable file raises `OSError` and exits through the normal traceback. That
is a caller error rather than a content problem.
