# Introduction

DSV Parser reads the swim-meet interchange files of the Deutscher Schwimm-Verband
(`.dsv5` through `.dsv8`, including the packed `.dsv8z`) into a typed data schema.

## Coverage

Format 6, 7 and 8 are transcribed from the official specifications and cover all
four Listarten with every element and attribute. Format 5 is read as well; its
layouts are derived from the Format 6 change log rather than from the Format 5
document, and the parser says so in a warning. Every version difference is one
marked line in one table, described in the [format reference](./dsv-format.md).

## Reading is tolerant

The reader does not raise on file content. A value it cannot represent becomes
`null` and produces a diagnostic that names the line, the element, the attribute
position and its German name from the spec. A caller therefore gets a partial
document plus a list of what was lost, which is what an import pipeline needs in
order to mark a file as partially imported instead of failing it.

## Three surfaces, one reader

The Python library, the CLI and the FastAPI service all go through the same code.
The service publishes the document schema as OpenAPI, so consumers in Go, Java or
TypeScript can generate a client instead of reimplementing the format.

## Where to go next

| | |
| --- | --- |
| [Getting Started](./getting-started.md) | Install, parse a file, run the service |
| [Architecture](./architecture.md) | Pipeline and the element table |
| [DSV Format](./dsv-format.md) | The format and the version differences |
| [Data Schema](./data-schema.md) | How the document is laid out |
| [HTTP API](./api.md) | Endpoints, payloads, client generation |
| [CLI](./cli.md) | Subcommands, flags, exit codes |
| [Extending](./extending.md) | Adding elements, versions and code lists |

## Out of scope

Writing DSV files is not implemented. The element table would be usable for a
writer and `core/values.py` already has the `format_*` counterparts, but nothing
consumes them yet. `dsv_parser/naming.py` does implement the file-naming
convention.

Cross-element validation is also out of scope. The reader checks that a line
matches its declared layout, not that a `STARTPN` refers to a `PNMELDUNG` that
exists. That check needs the assembled document and belongs in the consumer.
