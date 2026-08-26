# HTTP API

Optional extra: `uv sync --extra api`, then

```bash
uvicorn dsv_parser.api:app --host 0.0.0.0 --port 8000
# or: make serve   /   make up   (Docker)
```

The service is stateless and can be mounted into another app:

```python
app.include_router(dsv_parser.api.router, prefix="/dsv")
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/parse` | Parse an uploaded file into the document schema |
| `POST` | `/check` | Validate without returning the document |
| `GET` | `/spec` | The element table and every coded vocabulary |
| `GET` | `/health` | Liveness and the supported format versions |
| `GET` | `/openapi.json` | The full schema — generate your client from this |

### `POST /parse`

`multipart/form-data` with one `file` field. Query parameter `exclude_none=true`
drops null fields from the response, which is much smaller but gives a variable
shape — leave it off for a generated client.

```bash
curl -F file=@meet.DSV8 http://localhost:8000/parse
```

```json
{
  "filename": "meet.DSV8",
  "clean": true,
  "source": { "encoding": "utf-8", "zipped": false, "member": null },
  "document": { "file_type": "meet_results", "version": 8, "...": "..." },
  "diagnostics": []
}
```

A readable upload always returns 200. Content problems come back as diagnostics
rather than HTTP errors, since a partially readable file is a normal result. Check
`clean` and `diagnostics`, not the status code.

### `POST /check`

Returns the header, the per-block element counts and the diagnostics, without the
document. Useful for an ingest pipeline deciding whether to accept a file, and for
a UI reporting what is wrong with one a user just picked.

```json
{
  "filename": "meet.DSV8",
  "clean": false,
  "file_type": "meet_results",
  "version": 8,
  "source": { "encoding": "cp1252", "zipped": false, "member": null },
  "elements": { "sections": 4, "events": 62, "individual_results": 1841 },
  "diagnostics": [
    {
      "severity": "error",
      "message": "unknown Stroke code",
      "line": 412,
      "element": "WETTKAMPF",
      "attribute": 6,
      "field": "Technik",
      "value": "Z"
    }
  ]
}
```

### `GET /spec`

The element table as data: every element with its attributes, their German names
from the spec, types and applicability, plus every vocabulary as
`code → speaking value`. Generated from the table in `spec/elements.py`.

## Errors

| Status | When |
| --- | --- |
| 200 | Readable upload — including one with parse diagnostics |
| 413 | Upload above 32 MB (`MAX_UPLOAD_BYTES` in `api/routes.py`) |
| 422 | No `file` field |

## Using it from another language

`/openapi.json` publishes the same Pydantic model the library returns, so a
generated client has the exact types:

```bash
openapi-generator generate -i http://localhost:8000/openapi.json -g go -o ./dsv
npx openapi-typescript http://localhost:8000/openapi.json -o dsv.d.ts
```

Two things to keep in mind:

- Swim times are integer milliseconds. `null` means "no time" (the format's
  `00:00:00,00` placeholder) and is not the same as `0`.
- Coded values are speaking strings rather than file codes: `"freestyle"`, not
  `"F"`. `GET /spec` gives the mapping in both directions.

## Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Root log level |

There is nothing else to set.
