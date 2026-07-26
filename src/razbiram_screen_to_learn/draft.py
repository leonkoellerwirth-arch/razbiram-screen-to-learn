"""The human-fixable draft of a target deck, and the check that says when it is fixable no more.

``export.py`` answers "what may leave the machine". This module answers the question a person asks
first: *what did the extractor actually see, and what is missing?* It projects **every** card into
the target shape — including the ones the export blocked — leaving the unevidenced parts explicitly
empty (``correctAnswer: ""``, ``correctOptionIds: []``) instead of guessing them.

That is not a loophole in invariant 1. A draft is never exportable as it stands: ``check_deck``
rejects an empty answer, and the studio keeps Download disabled until it passes. What the draft
does is give invariant 3 — the human release gate — something to hold. The person marks the answer
the material shows, and the evidence for that answer becomes their explicit confirmation, which
invariant 1 names as qualifying.

The rules in ``check_deck`` are the same ones ``export.py`` enforces per family. They live here in
one function because a hand-edited deck has no Capture IR behind it to re-derive them from.
"""

from __future__ import annotations

from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import EXPORTABLE_TIERS, CaptureIR, Card
from razbiram_screen_to_learn.export import (
    MCQ_MAX_OPTIONS,
    MCQ_MIN_OPTIONS,
    REQUIRED_CAPABILITY,
    TARGET_PROFILE,
    deck_envelope,
)

#: Families this target can hold at all. Anything else (matching, typed, image-occlusion) is
#: reported as unsupported upstream and has no shape to draft into.
DRAFTABLE_FAMILIES = frozenset({"single-choice", "multiple-select", "true-false", "flashcard"})


def _evidenced(card: Card) -> bool:
    """Whether this card's answer may be shown as an answer at all.

    A card blocked for its evidence tier still *has* an answer in the IR — the extractor's reading
    of an ambiguous source. Carrying it into the draft would hand a person a pre-filled guess to
    confirm, and a wrong guess that someone confirms is indistinguishable from a fabricated answer.
    So an unqualified tier drafts as unanswered: the material, not the extractor, has the last word.
    """
    return card.answerEvidenceTier in EXPORTABLE_TIERS


def _draft_choice(card: Card, sequence: int) -> dict:
    options = card.options or []
    keep = _evidenced(card)
    if card.family == "multiple-select":
        drafted = [
            {"optionId": o.optionId, "text": o.text, "isCorrect": o.isCorrect and keep}
            for o in options
        ]
        return {
            "cardId": f"q-{sequence:04d}",
            "type": "mcq",
            "selectionMode": "multiple",
            "sourceId": card.sourceId,
            "question": dict(card.prompt.value),
            "options": drafted,
            "correctOptionIds": [o["optionId"] for o in drafted if o["isCorrect"]],
            "scoring": {
                "mode": card.scoring.mode if card.scoring else "all-or-nothing",
                "points": card.scoring.points if card.scoring else 1,
            },
        }

    drafted = [{"text": o.text, "isCorrect": o.isCorrect and keep} for o in options]
    correct = next((o for o in drafted if o["isCorrect"]), None)
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "mcq",
        "sourceId": card.sourceId,
        "question": dict(card.prompt.value),
        # Empty on purpose when nothing was evidenced — this is the field a person fills in.
        "correctAnswer": correct["text"] if correct else "",
        "options": drafted,
        "scoring": {"mode": "single-best-answer", "points": 1},
    }


def _draft_true_false(card: Card, sequence: int) -> dict:
    statement = card.statement or card.prompt
    labels = card.labels or {"true": "", "false": ""}
    true_label, false_label = labels.get("true", ""), labels.get("false", "")
    answered = card.answer is not None and _evidenced(card)
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "mcq",
        "sourceFormat": "true-false",
        "sourceId": card.sourceId,
        "question": dict(statement.value),
        "correctAnswer": ("" if not answered else (true_label if card.answer else false_label)),
        "options": [
            {"text": true_label, "isCorrect": bool(answered and card.answer)},
            {"text": false_label, "isCorrect": bool(answered and not card.answer)},
        ],
        "scoring": {"mode": "single-best-answer", "points": 1},
    }


def _draft_flashcard(card: Card, sequence: int) -> dict:
    front = dict(card.front.value) if card.front else {}
    back = dict(card.back.value) if card.back else {}
    return {
        "cardId": f"q-{sequence:04d}",
        "type": "flashcard",
        "sourceId": card.sourceId,
        "question": front or dict(card.prompt.value),
        "front": front,
        "back": back,
    }


@dataclass(frozen=True)
class DraftResult:
    """The draft deck, plus which Capture IR card each drafted card came from.

    The mapping exists because the target numbers cards ``q-0001…`` by position while the export's
    blocked list names them by their IR ``cardId``. Without it the studio could show "blocked:
    c-7f3a" next to a draft that contains no such id, and leave a person hunting.
    """

    deck: dict | None
    #: Capture IR ``cardId`` → drafted ``cardId``.
    card_ids: dict[str, str]


def draft_deck(document: CaptureIR, *, estimated_minutes: int | None = None) -> DraftResult:
    """Project every draftable card into the target shape, unevidenced fields left empty.

    ``deck`` is ``None`` when the document holds no card the target could ever represent, so a
    caller can tell "nothing to fix here" from "here is what to fix".
    """
    cards: list[dict] = []
    card_ids: dict[str, str] = {}
    for card in document.cards:
        if card.family not in DRAFTABLE_FAMILIES:
            continue
        sequence = len(cards) + 1
        if card.family == "true-false":
            cards.append(_draft_true_false(card, sequence))
        elif card.family == "flashcard":
            cards.append(_draft_flashcard(card, sequence))
        else:
            cards.append(_draft_choice(card, sequence))
        card_ids[card.cardId] = cards[-1]["cardId"]

    if not cards:
        return DraftResult(deck=None, card_ids={})
    return DraftResult(
        deck=deck_envelope(document, cards, estimated_minutes=estimated_minutes),
        card_ids=card_ids,
    )


def _check_option_bounds(card: dict, options: list, where: str) -> list[str]:
    if card.get("sourceFormat") == "true-false":
        if len(options) != 2:
            return [f"{where}: a true/false card needs exactly 2 options, has {len(options)}"]
        return []
    if not (MCQ_MIN_OPTIONS <= len(options) <= MCQ_MAX_OPTIONS):
        return [
            f"{where}: the target accepts {MCQ_MIN_OPTIONS}-{MCQ_MAX_OPTIONS} options per mcq "
            f"card; this card has {len(options)}"
        ]
    return []


def _check_mcq(card: dict, where: str, capabilities: set[str]) -> list[str]:
    options = card.get("options")
    if not isinstance(options, list):
        return [f"{where}: mcq needs an options list"]

    errors = _check_option_bounds(card, options, where)
    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict) or not str(option.get("text", "")).strip():
            errors.append(f"{where}: option {index} has no text")

    if card.get("selectionMode") == "multiple":
        required = REQUIRED_CAPABILITY["multiple-select"]
        if required not in capabilities:
            errors.append(f"{where}: the target does not declare {required}")
        flagged = {o.get("optionId") for o in options if isinstance(o, dict) and o.get("isCorrect")}
        declared = set(card.get("correctOptionIds") or [])
        if not declared:
            errors.append(f"{where}: mark at least one correct option (correctOptionIds is empty)")
        elif flagged != declared:
            errors.append(
                f"{where}: correctOptionIds {sorted(declared)} does not equal the options "
                f"flagged isCorrect {sorted(str(f) for f in flagged)}"
            )
        return errors

    if (
        card.get("sourceFormat") == "true-false"
        and (required := REQUIRED_CAPABILITY["true-false"]) not in capabilities
    ):
        errors.append(f"{where}: the target does not declare {required}")

    correct = [o for o in options if isinstance(o, dict) and o.get("isCorrect")]
    if len(correct) != 1:
        errors.append(f"{where}: mark exactly one correct option, {len(correct)} are marked")
    elif str(card.get("correctAnswer", "")).strip() != str(correct[0].get("text", "")).strip():
        errors.append(f"{where}: correctAnswer must repeat the text of the correct option")
    return errors


def _check_card(card: object, index: int, capabilities: set[str]) -> list[str]:
    where = f"card {index}"
    if not isinstance(card, dict):
        return [f"{where}: is not an object"]
    where = f"card {card.get('cardId') or index}"

    errors: list[str] = []
    question = card.get("question")
    if not isinstance(question, dict) or not any(str(v).strip() for v in question.values()):
        errors.append(f"{where}: the question is empty")

    kind = card.get("type")
    if kind == "mcq":
        errors.extend(_check_mcq(card, where, capabilities))
    elif kind == "flashcard":
        for side in ("front", "back"):
            value = card.get(side)
            if not isinstance(value, dict) or not any(str(v).strip() for v in value.values()):
                errors.append(f"{where}: the flashcard {side} is empty")
    else:
        errors.append(f"{where}: type {kind!r} is not supported by this target profile")
    return errors


def check_deck(deck: object, *, capabilities: set[str] | None = None) -> list[str]:
    """Return every reason this deck may not be exported. An empty list means it may.

    Written against a plain ``dict`` rather than the typed contracts on purpose: the input is a
    person's hand-edited JSON, so it may be malformed in ways no model would round-trip.
    """
    declared = capabilities if capabilities is not None else set()
    if not isinstance(deck, dict):
        return ["the deck is not a JSON object"]

    errors: list[str] = []
    if deck.get("schemaId") != TARGET_PROFILE:
        errors.append(f"schemaId must be {TARGET_PROFILE!r}, found {deck.get('schemaId')!r}")

    cards = deck.get("cards")
    if not isinstance(cards, list) or not cards:
        errors.append("the deck has no cards")
        return errors

    seen: set[str] = set()
    for index, card in enumerate(cards, start=1):
        errors.extend(_check_card(card, index, declared))
        if isinstance(card, dict):
            card_id = str(card.get("cardId", ""))
            if card_id in seen:
                errors.append(f"card {card_id}: duplicate cardId")
            seen.add(card_id)
    return errors
