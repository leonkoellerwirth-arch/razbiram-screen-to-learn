"""The loopback studio API.

The studio and the CLI must produce identical results from identical input — they share one
pipeline on purpose, so a divergence here means someone has forked the logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import razbiram_screen_to_learn.studio.server as server
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
    assert body["export"]["deck"]["meta"]["cardCount"] == 4
    assert body["export"]["blockedCardIds"] == []


def test_api_and_cli_agree(client: TestClient) -> None:
    """One pipeline, two front ends — BIBLE invariant 13 in executable form."""
    body = _upload(client).json()
    direct = process_markup(FIXTURE.read_text(encoding="utf-8"))
    assert body["captureIr"] == dump_document(direct.document)


def test_the_response_always_carries_the_block_channel(client: TestClient) -> None:
    """Nothing is blocked for the default target; the channel must still be present and typed.

    A client that only saw `blocked` when it was non-empty would be easy to write against by
    accident and would then silently skip the reason panel the day a card is blocked. The
    reason-carrying guarantee itself is asserted in test_pipeline, where a capability can be
    withheld.
    """
    body = _upload(client).json()
    assert body["export"]["blocked"] == []
    assert body["export"]["blockedCardIds"] == []


def test_unsupported_families_are_surfaced_not_dropped(client: TestClient) -> None:
    body = _upload(client).json()
    assert "q-image-occlusion" in body["unsupported"]


def test_the_response_carries_a_draft_and_the_targets_capabilities(client: TestClient) -> None:
    """The studio cannot show what was recognised, or judge an edit, without these two.

    They are unconditional for the same reason `blocked` is: a client written against a response
    that only sometimes carries them is a client that silently drops the panel later.
    """
    body = _upload(client).json()
    assert body["export"]["draft"]["cards"]
    assert body["export"]["capabilities"]


def test_an_edited_deck_is_judged_by_the_same_rules_as_the_export(client: TestClient) -> None:
    body = _upload(client).json()
    deck = body["export"]["deck"]
    capabilities = body["export"]["capabilities"]

    passed = client.post("/v1/deck/check", json={"deck": deck, "capabilities": capabilities}).json()
    assert passed["ok"] is True
    assert passed["errors"] == []
    # What a caller saves: the same deck with the draft's working notes gone.
    assert "status" not in passed["deck"]
    assert all("review" not in card for card in passed["deck"]["cards"])
    assert passed["config"]["decks"][deck["deckKey"]]
    assert passed["config"]["accessTier"] == "premium"

    deck["cards"][0]["correctAnswer"] = "an answer nobody offered"
    failed = client.post("/v1/deck/check", json={"deck": deck, "capabilities": capabilities}).json()
    assert failed["ok"] is False
    assert failed["config"] is None
    assert any("correctAnswer" in error for error in failed["errors"])


def test_a_draft_nobody_has_fixed_yet_is_refused(client: TestClient) -> None:
    """The gate — invariant 3. An unfixed draft carries no evidenced answer and may not leave."""
    body = client.post(
        "/v1/process",
        files={"file": ("q.txt", b"1. Which clause?\nA) 6.3\nB) 7.2\nC) 10.2\n", "text/plain")},
    ).json()
    assert body["export"]["deck"] is None

    verdict = client.post(
        "/v1/deck/check",
        json={"deck": body["export"]["draft"], "capabilities": body["export"]["capabilities"]},
    ).json()
    assert verdict["ok"] is False


def test_quizlet_import_uses_the_same_response_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    direct = process_markup(FIXTURE.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}

    def fake_import(url: str, *, term_locale: str, definition_locale: str):
        seen.update(url=url, term=term_locale, definition=definition_locale)
        return direct

    monkeypatch.setattr(server, "process_quizlet_url", fake_import)
    response = client.post(
        "/v1/quizlet/import",
        json={"url": "https://quizlet.com/demo", "termLocale": "es", "definitionLocale": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert seen == {"url": "https://quizlet.com/demo", "term": "es", "definition": "en"}
    assert body["captureIr"] == dump_document(direct.document)
    assert body["export"]["draft"]["cards"]


def test_quizlet_import_rejects_non_quizlet_urls(client: TestClient) -> None:
    response = client.post("/v1/quizlet/import", json={"url": "https://example.com/cards"})
    assert response.status_code == 400
    assert "quizlet.com" in response.json()["detail"]


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
