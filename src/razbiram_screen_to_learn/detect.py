"""Reference implementation of card-type detection.

``docs/architecture/CARD_TYPE_DETECTION.md`` is the specification; this is the executable form of
it, and ``docs/schemas/card-detection.vectors.json`` is the conformance suite both this and the
razbiram.com engine must satisfy.

A deck arriving at the product carries no marker saying where it came from, so every card has to be
classifiable from its own fields. Keeping the rule in one testable place — and shipping the vectors
next to it — is what stops two implementations from drifting apart.
"""

from __future__ import annotations

from typing import Literal

CardMode = Literal[
    "mcq-single",
    "mcq-true-false",
    "mcq-multiple",
    "flashcard",
    "typed",
    "matching",
    "image-occlusion",
    "unknown",
]

#: Types that are their own mode: no further discrimination needed.
_DIRECT_TYPES: dict[str, CardMode] = {
    "flashcard": "flashcard",
    "typed": "typed",
    "matching": "matching",
    "image-occlusion": "image-occlusion",
}


def detect_card_mode(card: dict) -> CardMode:
    """Classify one card. Ordered exactly as the specification table.

    Returns ``"unknown"`` rather than guessing. A caller must not render an unknown card: an
    unrecognised card rendered as MCQ becomes a plausible-looking wrong one, and the learner has no
    way to tell. Skip it and report it.
    """
    card_type = card.get("type")
    if not isinstance(card_type, str):
        return "unknown"

    direct = _DIRECT_TYPES.get(card_type)
    if direct is not None:
        return direct

    if card_type != "mcq":
        return "unknown"

    # A card carrying both markers is invalid; the schema rejects it. Detection refuses it too
    # rather than letting whichever branch is checked first win by accident.
    has_multiple = card.get("selectionMode") == "multiple"
    has_true_false = card.get("sourceFormat") == "true-false"
    if has_multiple and has_true_false:
        return "unknown"
    if has_multiple:
        return "mcq-multiple"
    if has_true_false:
        return "mcq-true-false"
    return "mcq-single"


#: Only these two shapes have a single answer string a learner could be asked to type.
_TYPED_PROMOTABLE: frozenset[CardMode] = frozenset({"mcq-single", "mcq-true-false"})


def is_typed_promotion_safe(card: dict) -> bool:
    """Whether the runtime may re-present this card as typed recall.

    Stated as an allowlist of modes rather than "not multiple-select". The difference matters at
    the edges: an ``unknown`` card must not be promoted either, because a card the engine could not
    classify is one whose answer semantics it does not know — and promoting it would ask the
    learner to type against a field that may not mean what it looks like.

    Multiple-select is excluded for the concrete reason that it has no single string to type; a
    typed prompt would mark a correct learner wrong. The format reinforces this by omitting
    ``correctAnswer`` on that shape, but the rule does not depend on that holding.
    """
    if detect_card_mode(card) not in _TYPED_PROMOTABLE:
        return False
    answer = card.get("correctAnswer")
    return isinstance(answer, str) and bool(answer.strip())
