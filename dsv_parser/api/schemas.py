"""Request and response envelopes of the HTTP surface.

The document schema itself lives in :mod:`dsv_parser.model` and is reused
verbatim, so the OpenAPI document FastAPI generates is the same schema the
library exposes — a client generated from ``/openapi.json`` in any language gets
exactly the types this parser produces.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..core.diagnostics import Diagnostic
from ..model.document import DsvDocument


class SourceInfo(BaseModel):
    """How the uploaded bytes were decoded."""

    model_config = ConfigDict(extra="forbid")

    encoding: str = Field(description="The encoding the file was decoded with.")
    zipped: bool = Field(description="Whether the upload was a ZIP-packed .DSV8z.")
    member: str | None = Field(default=None, description="Name of the archive member, when zipped.")


class ParseResponse(BaseModel):
    """The result of parsing one uploaded file."""

    model_config = ConfigDict(extra="forbid")

    filename: str | None = Field(
        default=None, description="The uploaded file's name, echoed back for correlation."
    )
    clean: bool = Field(description="True when no data was lost.")
    source: SourceInfo = Field(description="Decoding provenance.")
    document: DsvDocument = Field(description="The parsed document.")
    diagnostics: list[Diagnostic] = Field(
        default_factory=list, description="Everything the reader had to complain about."
    )


class CheckResponse(BaseModel):
    """The result of validating one uploaded file, without the document."""

    model_config = ConfigDict(extra="forbid")

    filename: str | None = Field(default=None, description="The uploaded file's name.")
    clean: bool = Field(description="True when no data was lost.")
    file_type: str | None = Field(default=None, description="Listart of the FORMAT element.")
    version: int | None = Field(default=None, description="Declared format version.")
    source: SourceInfo = Field(description="Decoding provenance.")
    elements: dict[str, int] = Field(
        default_factory=dict, description="Element counts per document block."
    )
    diagnostics: list[Diagnostic] = Field(
        default_factory=list, description="Errors and warnings, in file order."
    )


class HealthResponse(BaseModel):
    """Liveness payload."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Always 'ok' when the service is serving.")
    version: str = Field(description="The dsv-parser package version.")
    supported_formats: list[int] = Field(description="The DSV format versions understood.")
