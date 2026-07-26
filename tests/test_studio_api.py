"""The loopback studio API.

The studio and the CLI must produce identical results from identical input — they share one
pipeline on purpose, so a divergence here means someone has forked the logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from razbiram_screen_to_learn.contracts import dump_document
from razbiram_screen_to_learn.pipeline import process_markup
from razbiram_screen_to_learn.studio.server import MAX_UPLOAD_BYTES, create_app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / "fixture.html"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def _upload(client: TestClient, name: str = "fixture.html", body: bytes | None = None):
    payload = body if body is not None else FIXTURE.read_bytes()
    return client.post("/v1/process", files={"file": (name, payload, "text/html")})


def test_health_reports_a_version(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"]


def test_process_returns_the_full_result(client: TestClient) -> None:
    body = _upload(client).json()
    assert body["captureIr"]["schemaVersion"] == "capture-ir.v1"
    assert len(body["captureIr"]["cards"]) == 4
    assert body["export"]["deck"]["meta"]["cardCount"] == 2
    assert set(body["export"]["blockedCardIds"]) == {
        card["cardId"]
        for card in body["captureIr"]["cards"]
        if card["family"] in {"multiple-select", "true-false"}
    }


def test_api_and_cli_agree(client: TestClient) -> None:
    """One pipeline, two front ends — BIBLE invariant 13 in executable form."""
    body = _upload(client).json()
    direct = process_markup(FIXTURE.read_text(encoding="utf-8"))
    assert body["captureIr"] == dump_document(direct.document)


def test_blocked_cards_are_reported_with_a_reason(client: TestClient) -> None:
    body = _upload(client).json()
    assert body["export"]["blocked"]
    for blocked in body["export"]["blocked"]:
        assert blocked["reason"], "a blocked card without a reason is unreviewable"
        assert blocked["cardId"] and blocked["family"]


def test_unsupported_families_are_surfaced_not_dropped(client: TestClient) -> None:
    body = _upload(client).json()
    assert "q-image-occlusion" in body["unsupported"]


def test_unsupported_file_type_is_rejected(client: TestClient) -> None:
    response = _upload(client, name="deck.pdf", body=b"%PDF-1.7")
    assert response.status_code == 400
    assert ".pdf" in response.json()["detail"]


def test_non_utf8_input_is_rejected(client: TestClient) -> None:
    response = _upload(client, body=b"\xff\xfe\x00bad")
    assert response.status_code == 400
    assert "UTF-8" in response.json()["detail"]


def test_oversized_upload_is_rejected(client: TestClient) -> None:
    response = _upload(client, body=b"x" * (MAX_UPLOAD_BYTES + 1))
    assert response.status_code == 400
    assert "limit" in response.json()["detail"]
