"""End-to-end M0 slice: fixture HTML in, validated and capability-gated deck out.

This closes the loop the unit tests leave open — the generated Capture IR is validated against the
*committed JSON Schema*, not merely against the Pydantic models that produced it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from razbiram_screen_to_learn.contracts import dump_document
from razbiram_screen_to_learn.export import MCQ_MAX_OPTIONS, MCQ_MIN_OPTIONS
from razbiram_screen_to_learn.pipeline import LIVE_CAPABILITIES, process_markup

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "pages" / "fixture.html"
IR_SCHEMA = ROOT / "docs" / "schemas" / "capture-ir.v1.schema.json"

EXTENDED = set(LIVE_CAPABILITIES) | {"mcq.multiple-select.v1", "mcq.two-option.v1"}


@pytest.fixture(scope="module")
def markup() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class TestExtraction:
    def test_every_supported_family_is_extracted(self, markup: str) -> None:
        result = process_markup(markup)
        families = {card.family for card in result.document.cards}
        assert families == {"single-choice", "multiple-select", "true-false", "flashcard"}

    def test_image_occlusion_is_reported_unsupported_not_silently_dropped(
        self, markup: str
    ) -> None:
        """An extractor that quietly skips a card would hide work from the reviewer."""
        result = process_markup(markup)
        assert "q-image-occlusion" in result.unsupported

    def test_generated_ir_validates_against_the_committed_schema(self, markup: str) -> None:
        result = process_markup(markup)
        payload = dump_document(result.document)
        schema = json.loads(IR_SCHEMA.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path)
        )
        assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)

    def test_extraction_is_deterministic(self, markup: str) -> None:
        first = dump_document(process_markup(markup).document)
        second = dump_document(process_markup(markup).document)
        assert first == second

    def test_no_answer_is_invented(self, markup: str) -> None:
        """Correctness must come from the source's own key, never from the extractor."""
        result = process_markup(markup)
        for card in result.document.cards:
            assert card.answerEvidenceTier == "source-verified"
            for option in card.options or []:
                if option.isCorrect:
                    assert option.evidence, f"{card.cardId} has an unevidenced correct option"

    def test_true_false_keeps_its_own_family(self, markup: str) -> None:
        """BIBLE invariant 4: the semantic source type survives into the IR."""
        result = process_markup(markup)
        card = next(c for c in result.document.cards if c.family == "true-false")
        assert card.answer is True
        assert set(card.labels or {}) == {"true", "false"}


class TestCapabilityGate:
    def test_live_target_blocks_multiple_select_and_true_false(self, markup: str) -> None:
        result = process_markup(markup, capabilities=LIVE_CAPABILITIES)
        blocked = {b.family for b in result.export.blocked}
        assert blocked == {"multiple-select", "true-false"}
        assert result.export.deck is not None
        exported = {card["type"] for card in result.export.deck["cards"]}
        assert exported == {"mcq", "flashcard"}

    def test_extended_target_exports_everything(self, markup: str) -> None:
        result = process_markup(markup, capabilities=EXTENDED)
        assert result.export.blocked == []
        assert result.export.deck is not None
        assert result.export.deck["meta"]["cardCount"] == 4

    def test_multiple_select_is_never_collapsed(self, markup: str) -> None:
        """The failure this whole gate exists to prevent."""
        result = process_markup(markup, capabilities=EXTENDED)
        card = next(c for c in result.export.deck["cards"] if c.get("selectionMode") == "multiple")
        assert len(card["correctOptionIds"]) > 1
        assert sum(1 for o in card["options"] if o["isCorrect"]) == len(card["correctOptionIds"])

    def test_blocked_cards_never_reach_the_deck(self, markup: str) -> None:
        result = process_markup(markup, capabilities=LIVE_CAPABILITIES)
        exported_sources = {card["sourceId"] for card in result.export.deck["cards"]}
        blocked_ids = set(result.export.blocked_card_ids)
        for card in result.document.cards:
            if card.cardId in blocked_ids:
                assert card.sourceId not in exported_sources


class TestLiveTargetRules:
    """Rules read from razbiram.com's own validator, not from prose."""

    def test_mcq_option_count_is_within_the_live_bounds(self, markup: str) -> None:
        """Scoped to the live target on purpose.

        A two-option card only becomes legal once a target declares mcq.two-option.v1; under
        EXTENDED the true/false card is exported with two options by design.
        """
        result = process_markup(markup, capabilities=LIVE_CAPABILITIES)
        for card in result.export.deck["cards"]:
            if card["type"] == "mcq":
                assert MCQ_MIN_OPTIONS <= len(card["options"]) <= MCQ_MAX_OPTIONS

    def test_correct_answer_matches_an_option_text_exactly(self, markup: str) -> None:
        result = process_markup(markup, capabilities=EXTENDED)
        for card in result.export.deck["cards"]:
            if card["type"] == "mcq" and "correctAnswer" in card:
                texts = [option["text"] for option in card["options"]]
                assert card["correctAnswer"] in texts

    def test_card_count_matches_the_card_list(self, markup: str) -> None:
        result = process_markup(markup, capabilities=EXTENDED)
        deck = result.export.deck
        assert deck["meta"]["cardCount"] == len(deck["cards"])

    def test_exported_card_ids_are_sequential(self, markup: str) -> None:
        """Shipped decks run q-0001..q-00NN; stable identity travels in sourceId."""
        result = process_markup(markup, capabilities=EXTENDED)
        ids = [card["cardId"] for card in result.export.deck["cards"]]
        assert ids == [f"q-{index:04d}" for index in range(1, len(ids) + 1)]
        assert all(card["sourceId"].startswith("src_") for card in result.export.deck["cards"])
