"""Detection must agree with the vectors, and our own output must be detectable.

The vectors file is shipped for razbiram.com to test its engine against. If it only described what
this implementation happens to do, it would be worthless as a contract — so it is authored
separately and both sides are checked against it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from razbiram_screen_to_learn.detect import detect_card_mode, is_typed_promotion_safe
from razbiram_screen_to_learn.pipeline import process_markup

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads(
    (ROOT / "docs" / "schemas" / "card-detection.vectors.json").read_text(encoding="utf-8")
)
FIXTURE = ROOT / "fixtures" / "pages" / "fixture.html"


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_detection_matches_the_published_vectors(case: dict) -> None:
    assert detect_card_mode(case["card"]) == case["mode"]


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_typed_promotion_matches_the_published_vectors(case: dict) -> None:
    assert is_typed_promotion_safe(case["card"]) is case["typedPromotionSafe"]


def test_the_vector_file_covers_every_mode() -> None:
    """A conformance suite that skipped a mode would pass an engine that never implemented it."""
    covered = {case["mode"] for case in VECTORS["cases"]}
    assert covered == {
        "mcq-single",
        "mcq-true-false",
        "mcq-multiple",
        "flashcard",
        "typed",
        "matching",
        "image-occlusion",
        "unknown",
    }


class TestOurOutputIsDetectable:
    """Whatever we emit has to survive the same rule, or the deck is unusable on arrival."""

    @pytest.fixture(scope="class")
    def deck(self) -> dict:
        exported = process_markup(FIXTURE.read_text(encoding="utf-8")).export.deck
        assert exported is not None
        return exported

    def test_no_exported_card_is_unknown(self, deck: dict) -> None:
        modes = {card["cardId"]: detect_card_mode(card) for card in deck["cards"]}
        assert "unknown" not in modes.values(), modes

    def test_every_emitted_shape_is_detected_as_intended(self, deck: dict) -> None:
        modes = sorted(detect_card_mode(card) for card in deck["cards"])
        assert modes == ["flashcard", "mcq-multiple", "mcq-single", "mcq-true-false"]

    def test_multiple_select_omits_correct_answer(self, deck: dict) -> None:
        """The property that keeps typed promotion away from it without a special case."""
        card = next(c for c in deck["cards"] if detect_card_mode(c) == "mcq-multiple")
        assert "correctAnswer" not in card
        assert is_typed_promotion_safe(card) is False

    def test_single_answer_cards_stay_typed_promotable(self, deck: dict) -> None:
        card = next(c for c in deck["cards"] if detect_card_mode(c) == "mcq-single")
        assert is_typed_promotion_safe(card) is True
