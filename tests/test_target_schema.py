"""``learncard-target.v1`` is the whole integration boundary with razbiram.com.

The product does not import or know about screen-to-learn — it only has to parse this deck JSON.
So the schema has to be true in both directions at once: strict enough to specify the two additive
formats precisely, and loose enough to accept the decks that already ship. A schema that rejected
live content would not be a contract, it would be a wish.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from razbiram_screen_to_learn.pipeline import process_markup

ROOT = Path(__file__).resolve().parents[1]
TARGET_SCHEMA = ROOT / "docs" / "schemas" / "learncard-target.v1.schema.json"
FIXTURE = ROOT / "fixtures" / "pages" / "fixture.html"

#: The deck that ships in studywithme_db. Outside this repo, so the check skips when it is absent
#: rather than failing a clone that does not have the sibling checked out.
SHIPPED_DECK = (
    ROOT.parent
    / "studywithme_db"
    / "app"
    / "studywithme-bg"
    / "learncards"
    / "Biophysics"
    / "deck-01.json"
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(TARGET_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, document: dict) -> list[str]:
    return [
        f"{list(error.path)}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    ]


@pytest.mark.parametrize(
    "example",
    ["multiple-select.proposed.example.json", "true-false.compat.example.json"],
)
def test_committed_examples_conform(validator: Draft202012Validator, example: str) -> None:
    document = json.loads((ROOT / "docs" / "schemas" / example).read_text(encoding="utf-8"))
    assert not _errors(validator, document)


def test_our_export_conforms(validator: Draft202012Validator) -> None:
    deck = process_markup(FIXTURE.read_text(encoding="utf-8")).export.deck
    assert deck is not None
    assert not _errors(validator, deck)


def test_the_shipped_deck_still_conforms(validator: Draft202012Validator) -> None:
    """The additive formats must not invalidate content that already exists."""
    if not SHIPPED_DECK.exists():
        pytest.skip(f"{SHIPPED_DECK} not checked out")
    document = json.loads(SHIPPED_DECK.read_text(encoding="utf-8"))
    assert not _errors(validator, document)


class TestDiscriminatorsAreExplicit:
    """A parser must never have to infer the card shape from the option count."""

    def test_true_false_needs_its_marker_to_be_allowed_two_options(
        self, validator: Draft202012Validator
    ) -> None:
        document = json.loads(
            (ROOT / "docs" / "schemas" / "true-false.compat.example.json").read_text(
                encoding="utf-8"
            )
        )
        document["cards"][0].pop("sourceFormat")
        errors = _errors(validator, document)
        assert errors, "a two-option mcq without sourceFormat must be rejected"

    def test_multiple_select_needs_its_marker(self, validator: Draft202012Validator) -> None:
        document = json.loads(
            (ROOT / "docs" / "schemas" / "multiple-select.proposed.example.json").read_text(
                encoding="utf-8"
            )
        )
        document["cards"][0].pop("selectionMode")
        errors = _errors(validator, document)
        assert errors, "a multi-answer mcq without selectionMode must be rejected"

    def test_multiple_select_requires_an_answer_set(self, validator: Draft202012Validator) -> None:
        document = json.loads(
            (ROOT / "docs" / "schemas" / "multiple-select.proposed.example.json").read_text(
                encoding="utf-8"
            )
        )
        document["cards"][0]["correctOptionIds"] = []
        assert _errors(validator, document)

    def test_multiple_select_options_carry_stable_ids(
        self, validator: Draft202012Validator
    ) -> None:
        """Without optionId the answer set could only be expressed by text or position."""
        document = json.loads(
            (ROOT / "docs" / "schemas" / "multiple-select.proposed.example.json").read_text(
                encoding="utf-8"
            )
        )
        for option in document["cards"][0]["options"]:
            option.pop("optionId")
        assert _errors(validator, document)
