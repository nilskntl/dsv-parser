"""The HTTP endpoints.

Four routes, all stateless and all synchronous. Parsing is CPU-bound and fast
(a large meet protocol is a few megabytes of text), so the handlers are plain
``def`` — FastAPI runs those in a worker thread, which keeps the event loop free
without the ceremony of an executor.

Upload size is capped: the service is meant to be called by other services, and
an unbounded ``UploadFile`` read is the one way a caller can take the process
down with a single request.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse

from .. import __version__
from ..core.parser import ParseResult, parse_bytes
from ..spec.fields import VERSIONS
from ..spec.render import describe_registry
from .schemas import CheckResponse, HealthResponse, ParseResponse, SourceInfo

#: Refuse an upload larger than this. A DSV meet protocol for a large national
#: championship is well under 10 MB even uncompressed; 32 MB leaves generous room
#: while still bounding the memory one request can claim.
MAX_UPLOAD_BYTES = 32 * 1024 * 1024

router = APIRouter()


def _read_upload(upload: UploadFile) -> bytes:
    """Read an uploaded file, refusing anything oversized.

    Args:
        upload: The multipart upload.

    Returns:
        The raw bytes.

    Raises:
        HTTPException: 413 if the upload exceeds :data:`MAX_UPLOAD_BYTES`.
    """
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file exceeds the {MAX_UPLOAD_BYTES} byte limit",
        )
    return content


def _source(result: ParseResult) -> SourceInfo:
    """Project the decoding provenance onto its response model.

    Args:
        result: The parse result.

    Returns:
        The source info.
    """
    return SourceInfo(
        encoding=result.source.encoding,
        zipped=result.source.zipped,
        member=result.source.member,
    )


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Report liveness and what this build understands.

    Returns:
        The health payload.
    """
    return HealthResponse(status="ok", version=__version__, supported_formats=sorted(VERSIONS))


@router.get("/spec", tags=["meta"])
def spec() -> dict[str, object]:
    """Return the element table this parser implements.

    Generated from the table itself, so it can never drift from the reader.

    Returns:
        The elements and the coded vocabularies.
    """
    return describe_registry()


@router.post("/parse", response_model=ParseResponse, tags=["parse"])
def parse(
    file: UploadFile = File(description="A .dsv5–.dsv8 file, or a ZIP-packed .dsv8z."),
    exclude_none: bool = Query(
        default=False,
        description=(
            "Omit null fields from the document. Much smaller responses, at the cost "
            "of a variable shape — a generated client should leave this off."
        ),
    ),
) -> Response | ParseResponse:
    """Parse an uploaded DSV file into the typed document schema.

    The response is always 200 for a readable upload: content problems are
    reported as diagnostics, not as HTTP errors, because a partially readable
    file is a normal and useful outcome for the callers this serves.

    Args:
        file: The uploaded DSV file.
        exclude_none: Whether to drop null fields from the document.

    Returns:
        The document, its diagnostics and the decoding provenance. With
        ``exclude_none`` the pruned payload is written straight to the response:
        returning the model instead would have FastAPI re-serialise it through
        ``response_model``, which puts every null back.
    """
    result = parse_bytes(_read_upload(file))
    response = ParseResponse(
        filename=file.filename,
        clean=result.clean,
        source=_source(result),
        document=result.document,
        diagnostics=result.diagnostics.entries,
    )
    if exclude_none:
        return JSONResponse(response.model_dump(mode="json", exclude_none=True))
    return response


@router.post("/check", response_model=CheckResponse, tags=["parse"])
def check(
    file: UploadFile = File(description="A .dsv5–.dsv8 file, or a ZIP-packed .dsv8z."),
) -> CheckResponse:
    """Validate an uploaded DSV file without returning the document.

    The cheap call for an ingest pipeline that only needs to know whether a file
    is worth taking, and for a UI that wants to show the user what is wrong with
    the file they just picked.

    Args:
        file: The uploaded DSV file.

    Returns:
        The header, element counts and diagnostics.
    """
    result = parse_bytes(_read_upload(file))
    return CheckResponse(
        filename=file.filename,
        clean=result.clean,
        file_type=result.document.file_type.value if result.document.file_type else None,
        version=result.document.version,
        source=_source(result),
        elements=result.document.element_counts(),
        diagnostics=result.diagnostics.entries,
    )
