"""The draft a person edits, and the gate that judges it.

Two properties matter and the rest is detail: a draft must never be exportable as it stands
(invariant 1 — nothing unevidenced leaves), and a draft a person has actually fixed must be a
genuinely valid target deck (invariant 3 — the human release gate has to lead somewhere). The last
test asserts the second against the committed target schema, not against our own opinion of it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from razbiram_screen_to_learn.draft import check_deck, draft_deck
from razbiram_screen_to_learn.export import TARGET_PROFILE
from razbiram_screen_to_learn.pipeline import LIVE_CAPABILITIES, process_markup, process_text

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "pages" / "fixture.html"
TARGET_SCHEMA = ROOT / "docs" / "schemas" / "learncard-target.v1.schema.json"

#: A question whose answer the material never states — the case that produced an empty screen
#: before the draft existed: recognised, blocked, and nothing to look at.
NO_ANSWER_KEY = """\
1. Which clause covers competence?
A) Clause 6.3
B) Clause 7.2
C) Clause 10.2
D) Clause 4.2

2. Which clause covers internal audit?
A) Clause 9.2
B) Clause 8.1
C) Clause 5.3
D) Clause 6.1
"""


#: A true/false statement with no key. The extractor still forms an opinion about it, at a tier
#: that may not be exported — see `test_an_unqualified_answer_is_stripped_rather_than_offered`.
TRUE_FALSE_WITHOUT_A_KEY = """\
1. Annex A defines four categories to group the 93 controls.

a) True
b) False
"""


@pytest.fixture(scope="module")
def unevidenced():
    return process_text(NO_ANSWER_KEY, title="clauses")


class TestDraft:
    def test_blocked_cards_still_reach_the_draft(self, unevidenced) -> None:
        """The export is empty and the draft is not — that difference is the whole feature."""
        assert unevidenced.export.deck is None
        result = draft_deck(unevidenced.document)
        assert result.deck is not None
        assert len(result.deck["cards"]) == len(unevidenced.document.cards)

    def test_an_unevidenced_answer_is_left_empty_not_guessed(self, unevidenced) -> None:
        for card in draft_deck(unevidenced.document).deck["cards"]:
            assert card["correctAnswer"] == ""
            assert not any(option["isCorrect"] for option in card["options"])

    def test_the_draft_is_never_exportable_as_it_stands(self, unevidenced) -> None:
        errors = check_deck(draft_deck(unevidenced.document).deck, capabilities=LIVE_CAPABILITIES)
        assert errors
        assert any("exactly one correct option" in error for error in errors)

    def test_every_blocked_card_can_be_found_in_the_draft(self, unevidenced) -> None:
        result = draft_deck(unevidenced.document)
        drafted = {card["cardId"] for card in result.deck["cards"]}
        for blocked in unevidenced.export.blocked:
            assert result.card_ids[blocked.card_id] in drafted

    def test_an_unqualified_answer_is_stripped_rather_than_offered(self) -> None:
        """A true/false card the extractor answered at an unexportable tier drafts as unanswered.

        Found in the studio, not in a unit test: a real quiz produced three blocked cards, and only
        two of them showed a reason to fix. The third was a true/false whose answer the extractor
        had inferred from an ambiguous source — structurally complete, so the gate cleared it, and
        Download turned green on an answer nobody evidenced. Structure is not evidence.
        """
        result = process_text(TRUE_FALSE_WITHOUT_A_KEY, title="tf")
        card = result.document.cards[0]
        assert card.family == "true-false"
        assert card.answer is not None, "the extractor did read an answer — that is the trap"
        assert card.answerEvidenceTier not in ("source-verified", "reviewer-confirmed")

        drafted = draft_deck(result.document).deck["cards"][0]
        assert drafted["correctAnswer"] == ""
        assert not any(option["isCorrect"] for option in drafted["options"])
        assert check_deck(draft_deck(result.document).deck, capabilities=LIVE_CAPABILITIES)

    def test_the_draft_carries_the_same_envelope_as_the_export(self) -> None:
        """Metadata may not change on the way through the editor."""
        result = process_markup(FIXTURE.read_text(encoding="utf-8"))
        drafted = draft_deck(result.document).deck
        assert result.export.deck is not None
        assert drafted["meta"]["title"] == result.export.deck["meta"]["title"]
        assert drafted["deckKey"] == result.export.deck["deckKey"]

    def test_a_document_with_nothing_draftable_says_so(self, unevidenced) -> None:
        empty = unevidenced.document.model_copy(update={"cards": []})
        assert draft_deck(empty).deck is None


class TestCheckDeck:
    def test_a_real_export_passes(self) -> None:
        result = process_markup(FIXTURE.read_text(encoding="utf-8"))
        assert check_deck(result.export.deck, capabilities=LIVE_CAPABILITIES) == []

    def test_a_deck_with_no_cards_is_rejected(self) -> None:
        assert check_deck({"schemaId": TARGET_PROFILE, "cards": []})

    def test_a_foreign_schema_id_is_rejected(self) -> None:
        result = process_markup(FIXTURE.read_text(encoding="utf-8"))
        deck = json.loads(json.dumps(result.export.deck))
        deck["schemaId"] = "something.else.v1"
        assert any(
            "schemaId" in error for error in check_deck(deck, capabilities=LIVE_CAPABILITIES)
        )

    def test_a_correct_answer_that_matches_no_option_is_rejected(self) -> None:
        result = process_markup(FIXTURE.read_text(encoding="utf-8"))
        deck = json.loads(json.dumps(result.export.deck))
        deck["cards"][0]["correctAnswer"] = "an answer nobody offered"
        errors = check_deck(deck, capabilities=LIVE_CAPABILITIES)
        assert any("correctAnswer" in error for error in errors)

    def test_multiple_select_needs_the_declared_capability(self) -> None:
        deck = {
            "schemaId": TARGET_PROFILE,
            "cards": [
                {
                    "cardId": "q-0001",
                    "type": "mcq",
                    "selectionMode": "multiple",
                    "question": {"en": "Pick two"},
                    "options": [
                        {"optionId": "o1", "text": "a", "isCorrect": True},
                        {"optionId": "o2", "text": "b", "isCorrect": True},
                        {"optionId": "o3", "text": "c", "isCorrect": False},
                    ],
                    "correctOptionIds": ["o1", "o2"],
                }
            ],
        }
        assert check_deck(deck, capabilities=set()) != []
        assert check_deck(deck, capabilities={"mcq.multiple-select.v1"}) == []

    def test_garbage_is_reported_rather_than_raised(self) -> None:
        assert check_deck("not a deck")
        assert check_deck({"schemaId": TARGET_PROFILE, "cards": ["not a card"]})


def test_a_fixed_draft_is_a_valid_target_deck(unevidenced) -> None:
    """What a person does in the editor has to end somewhere real.

    Mark the answer the material shows, and the result must satisfy both our gate and the committed
    ``learncard-target.v1`` schema — the actual contract with razbiram.com.
    """
    deck = draft_deck(unevidenced.document).deck
    for card in deck["cards"]:
        card["options"][0]["isCorrect"] = True
        card["correctAnswer"] = card["options"][0]["text"]

    assert check_deck(deck, capabilities=LIVE_CAPABILITIES) == []

    schema = json.loads(TARGET_SCHEMA.read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(deck))
