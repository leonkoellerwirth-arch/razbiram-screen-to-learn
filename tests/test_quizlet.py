from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from razbiram_screen_to_learn.cli import main
from razbiram_screen_to_learn.quizlet import process_quizlet_payloads

ROOT = Path(__file__).resolve().parents[1]
TARGET_SCHEMA = ROOT / "docs" / "schemas" / "learncard-target.v1.schema.json"


def _raw_item(item_id: int, rank: int, front: str, back: str) -> dict:
    return {
        "id": item_id,
        "rank": rank,
        "cardSides": [
            {
                "label": "word",
                "media": [{"plainText": front}],
            },
            {
                "label": "definition",
                "media": [{"plainText": back}],
            },
        ],
    }


def _set_payload(*items: dict) -> str:
    state = {
        "setPage": {
            "set": {
                "id": 870874497,
                "title": "ISO/ IEC 27001 : 2022 Lead Auditor",
                "description": "Lead auditor flashcards",
                "numTerms": 3,
            },
            "pagingMeta": {
                "page": 1,
                "perPage": 100,
                "token": "token",
                "total": 3,
            },
        },
        "studyModesCommon": {
            "studiableData": {
                "studiableItems": list(items),
            },
        },
    }
    next_data = {"props": {"pageProps": {"dehydratedReduxStateKey": json.dumps(state)}}}
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>'


def _api_payload(*items: dict) -> str:
    return json.dumps(
        {
            "responses": [
                {
                    "models": {"studiableItem": list(items)},
                    "paging": {
                        "total": 3,
                        "page": 2,
                        "perPage": 100,
                        "token": "token",
                    },
                }
            ]
        }
    )


def test_quizlet_payloads_export_all_captured_pages() -> None:
    result = process_quizlet_payloads(
        _set_payload(
            _raw_item(1, 0, "Front 1", "Back 1"),
            _raw_item(2, 1, "Front 2", "Back 2"),
        ),
        api_payloads=[_api_payload(_raw_item(3, 2, "Front 3", "Back 3"))],
        path="/es/870874497/iso-iec-27001-2022-lead-auditor-flash-cards/",
        term_locale="es",
        definition_locale="en",
    )

    assert result.issues == []
    assert result.export.deck is not None
    assert result.export.deck["meta"]["cardCount"] == 3
    assert [card["cardId"] for card in result.export.deck["cards"]] == [
        "q-0001",
        "q-0002",
        "q-0003",
    ]
    assert result.export.deck["meta"]["languages"] == {"source": "es", "target": "en"}
    assert [card["front"]["es"] for card in result.export.deck["cards"]] == [
        "Front 1",
        "Front 2",
        "Front 3",
    ]
    assert result.export.deck["cards"][0]["back"]["en"] == "Back 1"


def test_quizlet_export_conforms_to_target_schema() -> None:
    result = process_quizlet_payloads(
        _set_payload(_raw_item(1, 0, "What is ISO 27001?", "An ISMS standard.")),
    )
    deck = result.export.deck
    assert deck is not None

    schema = json.loads(TARGET_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(deck), key=lambda error: list(error.path)
    )
    assert not errors


def test_quizlet_import_cli_writes_deck(tmp_path: Path) -> None:
    set_file = tmp_path / "set.html"
    api_file = tmp_path / "page-2.json"
    output = tmp_path / "deck.json"
    set_file.write_text(_set_payload(_raw_item(1, 0, "Front 1", "Back 1")), encoding="utf-8")
    api_file.write_text(_api_payload(_raw_item(2, 1, "Front 2", "Back 2")), encoding="utf-8")

    code = main(
        [
            "quizlet-import",
            str(set_file),
            "--api-payload",
            str(api_file),
            "--term-locale",
            "es",
            "--definition-locale",
            "en",
            "-o",
            str(output),
        ]
    )

    assert code == 0
    deck = json.loads(output.read_text(encoding="utf-8"))
    assert deck["schemaId"] == "studywithme-bg.learncard.v1"
    assert deck["meta"]["cardCount"] == 2
    assert deck["meta"]["languages"] == {"source": "es", "target": "en"}
