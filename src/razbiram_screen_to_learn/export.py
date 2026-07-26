"""Capability-gated projection from Capture IR to the live target deck.

The target is ``studywithme-bg.learncard.v1``, verified against the reference deck in
``studywithme_db``. Every rule below is read from the code that actually accepts our decks —
``app/src/lib/learncards/helpers.ts`` (``isLearnCardShape``) and the adapters behind it — never
from prose. Note which validator that is *not*: ``deckSchema.ts`` governs ``recall.deck.v1``, a
different contract for a different product, and reading a rule out of it once cost us legitimate
cards (see ``MCQ_MIN_OPTIONS``).

Nothing is ever degraded to fit. A card the target cannot represent losslessly is blocked and
reported, per BIBLE invariant 5.
"""

from __future__ import annotations

from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import EXPORTABLE_TIERS, CaptureIR, Card

TARGET_PROFILE = "studywithme-bg.learncard.v1"

#: An mcq card needs at least two options; the target sets no upper bound.
#:
#: This was 3-5 until 2026-07-27, cited to `deckSchema.ts` in razbiram.com. That citation was to
#: the wrong contract: `deckSchema.ts` validates `recall.deck.v1` and runs only on decks that
#: declare `schema: "recall.deck.v1"` (its `declaresDeckV1` tripwire). A deck of ours declares
#: `studywithme-bg.learncard.v1`, which the product accepts through `helpers.ts:isLearnCardShape` —
#: no option-count rule there at all, and its adapters require two. The old bound therefore refused
#: legitimate material: a real six-option exam question was blocked by a rule that never governed
#: it. A true/false card keeps exactly two options, which its own branch enforces.
MCQ_MIN_OPTIONS = 2

#: Capability identifiers a target must declare before the matching family may be exported.
REQUIRED_CAPABILITY = {
    "multiple-select": "mcq.multiple-select.v1",
    "true-false": "mcq.true-false",
}


@dataclass(frozen=True)
class BlockedCard:
    card_id: str
    family: str
    reason: str


@dataclass
class ExportResult:
    deck: dict | None
    blocked: list[BlockedCard]

    @property
    def blocked_card_ids(self) -> list[str]:
        return [item.card_id for item in self.blocked]


def _localized(field_value: dict[str, str]) -> dict[str, str]:
    return dict(field_value)


def _block(card: Card, reason: str) -> BlockedCard:
    return BlockedCard(card_id=card.cardId, family=card.family, reason=reason)


def _export_single_choice(card: Card, sequence: int) -> tuple[dict | None, BlockedCard | None]:
    options = card.options or []
    if len(options) < MCQ_MIN_OPTIONS:
        return None, _block(
            card,
            f"an mcq card needs at least {MCQ_MIN_OPTIONS} options; this card has {len(options)}",
        )
    correct = [option for option in options if option.isCorrect]
    if len(correct) != 1:
        return None, _block(
            card, f"single-choice needs exactly one correct option, has {len(correct)}"
        )
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "mcq",
        "sourceId": card.sourceId,
        "question": _localized(card.prompt.value),
        # The live validator matches `correctAnswer` against option text exactly.
        "correctAnswer": correct[0].text,
        "options": [{"text": option.text, "isCorrect": option.isCorrect} for option in options],
        "scoring": {"mode": "single-best-answer", "points": 1},
    }, None


def _export_flashcard(card: Card, sequence: int) -> tuple[dict | None, BlockedCard | None]:
    if card.front is None or card.back is None:
        return None, _block(card, "flashcard needs front and back")
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "flashcard",
        "sourceId": card.sourceId,
        "question": _localized(card.front.value),
        "front": _localized(card.front.value),
        "back": _localized(card.back.value),
    }, None


def _export_true_false(card: Card, sequence: int) -> tuple[dict | None, BlockedCard | None]:
    """Project the semantic true/false family onto the target's two-option MCQ shape.

    Reachable only when the target declares ``mcq.true-false``. The IR keeps true/false as its
    own family and it becomes a two-option MCQ here, at the boundary — never earlier.
    """
    if card.answer is None or not card.labels:
        return None, _block(card, "true-false needs an answer and both labels")
    statement = card.statement or card.prompt
    true_label = card.labels["true"]
    false_label = card.labels["false"]
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "mcq",
        "sourceFormat": "true-false",
        "sourceId": card.sourceId,
        "question": _localized(statement.value),
        "correctAnswer": true_label if card.answer else false_label,
        "options": [
            {"text": true_label, "isCorrect": bool(card.answer)},
            {"text": false_label, "isCorrect": not card.answer},
        ],
        "scoring": {"mode": "single-best-answer", "points": 1},
    }, None


def _export_multiple_select(card: Card, sequence: int) -> tuple[dict | None, BlockedCard | None]:
    """Emit the additive multiple-select shape proposed in DATA_CONTRACTS.md.

    Reachable only when the target declares ``mcq.multiple-select.v1``. Today's razbiram.com does
    not: its runtime, type and validator are all single-answer. The shape itself is still a
    proposal awaiting a coordinated schema decision, so the capability flag is what says a target
    has actually adopted it — never an assumption made here.
    """
    options = card.options or []
    if len(options) < MCQ_MIN_OPTIONS:
        return None, _block(
            card,
            f"an mcq card needs at least {MCQ_MIN_OPTIONS} options; this card has {len(options)}",
        )
    correct = [option.optionId for option in options if option.isCorrect]
    if not correct:
        return None, _block(card, "multiple-select needs at least one correct option")
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "mcq",
        "selectionMode": "multiple",
        "sourceId": card.sourceId,
        "question": _localized(card.prompt.value),
        "options": [
            {"optionId": o.optionId, "text": o.text, "isCorrect": o.isCorrect} for o in options
        ],
        "correctOptionIds": correct,
        "scoring": {
            "mode": card.scoring.mode if card.scoring else "all-or-nothing",
            "points": card.scoring.points if card.scoring else 1,
        },
    }, None


def _export_card(
    card: Card, sequence: int, capabilities: set[str]
) -> tuple[dict | None, BlockedCard | None]:
    # Correctness tier first, before any family logic. `validate_for_export` reports this too, but
    # a caller that reads `export.deck` without inspecting the issues must not receive a card whose
    # answer was never evidenced. Until the text path existed every card was `source-verified`, so
    # nothing had yet exercised this route — the structural checks below merely happened to catch
    # it. Defence belongs where the deck is actually built (BIBLE invariants 1 and 3).
    if card.answerEvidenceTier is None:
        return None, _block(card, "no answerEvidenceTier; an unevidenced answer cannot be exported")
    if card.answerEvidenceTier not in EXPORTABLE_TIERS:
        return None, _block(
            card,
            f"answerEvidenceTier {card.answerEvidenceTier!r} is not exportable; "
            f"needs one of {sorted(EXPORTABLE_TIERS)}",
        )

    required = REQUIRED_CAPABILITY.get(card.family)
    if required and required not in capabilities:
        if card.family == "multiple-select":
            reason = (
                f"target does not declare {required}; a multiple-select card is blocked rather "
                "than collapsed into a single answer"
            )
        else:
            reason = (
                f"target does not declare {required}; without it a two-option card carries no "
                "signal that its two options are a statement's truth values"
            )
        return None, _block(card, reason)

    if card.family == "single-choice":
        return _export_single_choice(card, sequence)
    if card.family == "flashcard":
        return _export_flashcard(card, sequence)
    if card.family == "true-false":
        return _export_true_false(card, sequence)
    if card.family == "multiple-select":
        return _export_multiple_select(card, sequence)
    return None, _block(card, f"family {card.family!r} is not supported by this target profile")


def export_deck(
    document: CaptureIR,
    *,
    capabilities: set[str] | None = None,
    estimated_minutes: int | None = None,
) -> ExportResult:
    """Project approved-shape Capture IR into a target deck.

    ``capabilities`` defaults to what the document's target declares. Blocked cards never appear in
    the deck and are always reported, so a caller cannot mistake a partial export for a full one.
    """
    declared = capabilities if capabilities is not None else set(document.target.capabilities)

    cards: list[dict] = []
    blocked: list[BlockedCard] = []
    for card in document.cards:
        exported, block = _export_card(card, len(cards) + 1, declared)
        if exported is not None:
            cards.append(exported)
        if block is not None:
            blocked.append(block)

    if not cards:
        return ExportResult(deck=None, blocked=blocked)

    return ExportResult(
        deck=deck_envelope(document, cards, estimated_minutes=estimated_minutes),
        blocked=blocked,
    )


def deck_envelope(
    document: CaptureIR, cards: list[dict], *, estimated_minutes: int | None = None
) -> dict:
    """Wrap already-projected cards in the target deck envelope.

    Shared with ``draft.py`` so the export and the draft a person edits differ in their cards and
    in nothing else — a draft that reaches export must not arrive with different metadata.
    """
    deck = document.deck
    return {
        "schemaId": TARGET_PROFILE,
        "deckKey": deck.deckKey,
        "bookKey": deck.bookKey,
        "meta": {
            "title": _localized(deck.title),
            "description": _localized(deck.description),
            "level": deck.level,
            "tags": list(deck.tags),
            "difficulty": deck.difficulty,
            # Written explicitly even though the loader can derive them.
            "estimatedMinutes": (
                estimated_minutes if estimated_minutes is not None else len(cards)
            ),
            "cardCount": len(cards),
            "languages": dict(deck.languages),
            "source": {
                "kind": document.source.kind,
                "rightsBasis": _rights_basis(document),
            },
        },
        "cards": cards,
    }


def _rights_basis(document: CaptureIR) -> str:
    bases = {card.rights.basis for card in document.cards}
    return bases.pop() if len(bases) == 1 else "unconfirmed"
