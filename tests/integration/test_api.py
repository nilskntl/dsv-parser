"""The HTTP surface, against the real FastAPI application."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dsv_parser.api import create_app
from dsv_parser.api.routes import MAX_UPLOAD_BYTES

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _upload(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {"file": (path.name, path.read_bytes(), "application/octet-stream")}


def test_health_reports_the_supported_formats(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["supported_formats"] == [5, 6, 7, 8]


def test_spec_lists_elements_and_vocabularies(client: TestClient) -> None:
    body = client.get("/spec").json()
    assert any(element["element"] == "WETTKAMPF" for element in body["elements"])
    assert body["vocabularies"]["Stroke"]["F"] == "freestyle"


def test_parse_returns_the_document(client: TestClient, fixtures: Path) -> None:
    response = client.post("/parse", files=_upload(fixtures / "results.dsv8"))
    assert response.status_code == 200
    body = response.json()
    assert body["clean"] is True
    assert body["filename"] == "results.dsv8"
    assert body["source"]["encoding"] == "utf-8"
    assert len(body["document"]["individual_results"]) == 2


def test_parse_reports_diagnostics_without_failing(client: TestClient, fixtures: Path) -> None:
    body = client.post("/parse", files=_upload(fixtures / "broken.dsv7")).json()
    assert body["clean"] is False
    assert any(entry["severity"] == "error" for entry in body["diagnostics"])
    # A partially readable file is a normal outcome, not an HTTP error.
    assert body["document"]["events"]


def test_parse_exclude_none_shrinks_the_payload(client: TestClient, fixtures: Path) -> None:
    files = _upload(fixtures / "definition.dsv7")
    full = client.post("/parse", files=files).content
    files = _upload(fixtures / "definition.dsv7")
    pruned = client.post("/parse?exclude_none=true", files=files).content
    assert len(pruned) < len(full)


def test_check_omits_the_document(client: TestClient, fixtures: Path) -> None:
    body = client.post("/check", files=_upload(fixtures / "definition.dsv7")).json()
    assert body["file_type"] == "definition"
    assert body["version"] == 7
    assert body["elements"]["events"] == 4
    assert "document" not in body


def test_oversized_upload_is_rejected(client: TestClient) -> None:
    payload = b"X" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/parse", files={"file": ("huge.dsv8", payload, "application/octet-stream")}
    )
    assert response.status_code == 413


def test_openapi_publishes_the_document_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "DsvDocument" in schema["components"]["schemas"]
