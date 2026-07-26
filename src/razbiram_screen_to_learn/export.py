"""Capability-gated projection from Capture IR to the live target deck.

The target is ``studywithme-bg.learncard.v1``, verified against the reference deck in
``studywithme_db``. Every rule below was checked against the live razbiram.com validator
(``app/src/lib/learncards/deckSchema.ts``) rather than taken from prose, because the documented
contract and the shipped one diverge in two places that matter.

Nothing is ever degraded to fit. A card the target cannot represent losslessly is blocked and
reported, per BIBLE invariant 5.
"""

from __future__ import annotations

from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import CaptureIR, Card

TARGET_PROFILE = "studywithme-bg.learncard.v1"

#: The target validator requires 3-5 options per mcq card (deckSchema.ts:200 at the pinned
#: commit). A true/false card is the documented exception and carries `sourceFormat: "true-false"`
#: with exactly two options; the razbiram.com change that accepts it is in progress, and this
#: bound is not applied to that path.
MCQ_MIN_OPTIONS = 3
MCQ_MAX_OPTIONS = 5

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
    if not (MCQ_MIN_OPTIONS <= len(options) <= MCQ_MAX_OPTIONS):
        return None, _block(
            card,
            f"the target accepts {MCQ_MIN_OPTIONS}-{MCQ_MAX_OPTIONS} options per mcq card; "
            f"this card has {len(options)}",
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
    if not (MCQ_MIN_OPTIONS <= len(options) <= MCQ_MAX_OPTIONS):
        return None, _block(
            card,
            f"the target accepts {MCQ_MIN_OPTIONS}-{MCQ_MAX_OPTIONS} options per mcq card; "
            f"this card has {len(options)}",
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
    required = REQUIRED_CAPABILITY.get(card.family)
    if required and required not in capabilities:
        if card.family == "multiple-select":
            reason = (
                f"target does not declare {required}; a multiple-select card is blocked rather "
                "than collapsed into a single answer"
            )
        else:
            reason = (
                f"target does not declare {required}; the live validator requires "
                f"{MCQ_MIN_OPTIONS}-{MCQ_MAX_OPTIONS} mcq options and has no true/false exception, "
                "so a two-option card would be rejected"
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

    deck = document.deck
    return ExportResult(
        deck={
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
        },
        blocked=blocked,
    )


def _rights_basis(document: CaptureIR) -> str:
    bases = {card.rights.basis for card in document.cards}
    return bases.pop() if len(bases) == 1 else "unconfirmed"
