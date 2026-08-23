# Getting Started

## Install

```bash
make install          # uv sync --extra api
```

The `api` extra adds FastAPI and uvicorn. The parsing core needs only Pydantic:

```bash
uv add dsv-parser              # library only
uv add "dsv-parser[api]"       # with the HTTP service
```

## Parse a file

```python
from dsv_parser import parse_file

result = parse_file("2026-06-13-Berlin-Pr.DSV8")
```

`ParseResult` has three parts:

| Attribute     | Contents                                                              |
| ------------- | --------------------------------------------------------------------- |
| `document`    | The parsed [`DsvDocument`](./data-schema.md), never `None`             |
| `diagnostics` | Errors and warnings collected while reading                            |
| `source`      | How the bytes were decoded: encoding, and whether the file was zipped  |

```python
document = result.document
print(document.file_type, document.version)  # meet_results 8
print(document.meet.name, document.meet.city)
print(document.element_counts())  # {'sections': 4, 'events': 62, …}

for swim in document.individual_results:
    print(swim.place, swim.name, swim.time_millis)  # milliseconds, None = no time
```

Two more entry points take bytes or already-decoded text:

```python
from dsv_parser import parse_bytes, parse_text

parse_bytes(upload.read())  # unwraps .dsv8z on its own
parse_text(source)  # when you decoded the file yourself
```

## Handle diagnostics

```python
if not result.clean:
    for entry in result.diagnostics.errors:  # data was lost
        print(entry.render())
    for entry in result.diagnostics.warnings:  # recovered
        print(entry.render())
```

```text
error: line 412 (WETTKAMPF#6 Technik): unknown Stroke code
warning: line 1204 (VEREIN): 2 attribute(s) beyond the 4 this layout declares, ignored
```

Each `Diagnostic` carries `severity`, `message`, `line`, `element`, `attribute`,
`field` (the German name from the spec) and the offending `value`, so a UI can
point at the exact position in the file. `render()` is only a convenience format.

`parse_file` does raise `OSError` when the file cannot be read at all. An
unreadable file is a caller error; a malformed one is not.

## From the command line

```bash
dsv-parser parse meet.DSV8 -o meet.json    # document as JSON
dsv-parser check meet.DSV8                 # validate, exit 1 on data loss
dsv-parser spec                            # the element table
```

Diagnostics go to stderr and the document to stdout, so
`dsv-parser parse meet.DSV8 > meet.json` writes clean JSON and still shows the
problems. Full reference: [CLI](./cli.md).

## As a service

```bash
make serve            # uvicorn on :8000 with reload
make up               # the same in Docker
```

```bash
curl -F file=@meet.DSV8 http://localhost:8000/parse
```

Interactive docs at `http://localhost:8000/docs`, the schema at `/openapi.json`.
Full reference: [HTTP API](./api.md).
