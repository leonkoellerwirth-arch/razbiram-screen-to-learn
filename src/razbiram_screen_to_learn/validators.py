"""Cross-field validation for ``capture-ir.v1``.

JSON Schema 2020-12 cannot express any of these rules, so they are code duties. They are listed as
such in ``docs/architecture/DATA_CONTRACTS.md`` and ``docs/architecture/QUALITY_AND_CI.md``.

The rules encode two BIBLE invariants that a plausible-looking change breaks first:

* evidence before generation — an answer must trace to qualifying evidence (invariant 1);
* lossless card semantics — multiple-select is never collapsed to a single answer (invariant 4).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import EXPORTABLE_TIERS, CaptureIR, Card


@dataclass(frozen=True)
class Issue:
    """One validation finding. ``blocking`` issues stop an export; warnings do not."""

    code: str
    message: str
    blocking: bool = True
    card_id: str | None = None

    def __str__(self) -> str:
        scope = f" [{self.card_id}]" if self.card_id else ""
        return f"{'BLOCKING' if self.blocking else 'warning'} {self.code}{scope}: {self.message}"


def _check_option_sets(card: Card) -> list[Issue]:
    """correctOptionIds must equal the set of options flagged isCorrect."""
    if card.options is None or card.correctOptionIds is None:
        return []
    flagged = {option.optionId for option in card.options if option.isCorrect}
    declared = set(card.correctOptionIds)
    if flagged != declared:
        return [
            Issue(
                "option-set-mismatch",
                f"correctOptionIds {sorted(declared)} does not equal the options flagged "
                f"isCorrect {sorted(flagged)}",
                card_id=card.cardId,
            )
        ]
    return []


def _check_duplicate_options(card: Card) -> list[Issue]:
    """Colliding option ids are an error.

    IDENTITY_ALGORITHMS.md requires a duplicate-option error rather than a silent merge.
    """
    if not card.options:
        return []
    issues: list[Issue] = []
    for option_id, count in Counter(o.optionId for o in card.options).items():
        if count > 1:
            issues.append(
                Issue(
                    "duplicate-option-id",
                    f"optionId {option_id} appears {count} times; identical option text on one "
                    "question is an error, never a silent merge",
                    card_id=card.cardId,
                )
            )
    return issues


def _check_family_rules(card: Card) -> list[Issue]:
    issues: list[Issue] = []
    correct = set(card.correctOptionIds or ())

    if card.family == "single-choice" and len(correct) != 1:
        issues.append(
            Issue(
                "single-choice-cardinality",
                f"single-choice needs exactly one correct option, found {len(correct)}",
                card_id=card.cardId,
            )
        )
    if card.family == "multiple-select" and not correct:
        issues.append(
            Issue(
                "multiple-select-empty",
                "multiple-select needs at least one correct option",
                card_id=card.cardId,
            )
        )
    if card.family == "true-false":
        labels = card.labels or {}
        if set(labels) != {"true", "false"}:
            issues.append(
                Issue(
                    "true-false-labels",
                    f"true-false needs exactly the labels true and false, found {sorted(labels)}",
                    card_id=card.cardId,
                )
            )
    if card.family == "typed" and not (card.acceptableAnswers or []):
        issues.append(
            Issue(
                "typed-no-answer",
                "typed needs at least one acceptable answer",
                card_id=card.cardId,
            )
        )
    if card.family == "flashcard" and (card.front is None or card.back is None):
        issues.append(
            Issue("flashcard-incomplete", "flashcard needs front and back", card_id=card.cardId)
        )
    if card.family == "matching":
        left = {item.get("itemId") for item in card.leftItems or []}
        right = {item.get("itemId") for item in card.rightItems or []}
        for pair in card.correctPairs or []:
            if pair.get("leftId") not in left or pair.get("rightId") not in right:
                issues.append(
                    Issue(
                        "matching-dangling-pair",
                        f"correctPair {pair} references an item that does not exist",
                        card_id=card.cardId,
                    )
                )
    return issues


def _check_answer_evidence(card: Card) -> list[Issue]:
    """BIBLE invariant 1: an exported answer must be source-verified or reviewer-confirmed."""
    if card.answerEvidenceTier is None:
        return [
            Issue(
                "missing-evidence-tier",
                "no answerEvidenceTier; an answer without an evidence tier cannot be exported",
                card_id=card.cardId,
            )
        ]
    if card.answerEvidenceTier not in EXPORTABLE_TIERS:
        return [
            Issue(
                "unqualified-evidence",
                f"answerEvidenceTier {card.answerEvidenceTier!r} is not exportable; "
                f"needs one of {sorted(EXPORTABLE_TIERS)}",
                card_id=card.cardId,
            )
        ]
    return []


def _check_evidence_references(document: CaptureIR) -> list[Issue]:
    """Every referenced evidenceId must exist in the ledger."""
    declared = {record.evidenceId for record in document.evidence}
    referenced: set[str] = set()
    for card in document.cards:
        for field in (card.prompt, card.statement, card.front, card.back):
            if field is not None:
                referenced.update(field.evidence)
        for option in card.options or []:
            referenced.update(option.evidence)
    dangling = referenced - declared
    if dangling:
        return [
            Issue(
                "dangling-evidence",
                f"cards reference evidence ids that the ledger does not define: {sorted(dangling)}",
            )
        ]
    return []


def _check_unique_card_ids(document: CaptureIR) -> list[Issue]:
    issues = []
    for card_id, count in Counter(card.cardId for card in document.cards).items():
        if count > 1:
            issues.append(Issue("duplicate-card-id", f"cardId {card_id} appears {count} times"))
    return issues


def _check_unresolved_review(card: Card) -> list[Issue]:
    """BIBLE invariant 3: export is never silently automatic."""
    if card.review.blockingReasons:
        return [
            Issue(
                "unresolved-review",
                f"unresolved blocking reasons: {card.review.blockingReasons}",
                card_id=card.cardId,
            )
        ]
    return []


def validate_document(document: CaptureIR) -> list[Issue]:
    """Run every cross-field rule. An empty list means the document is internally consistent."""
    issues: list[Issue] = []
    issues.extend(_check_evidence_references(document))
    issues.extend(_check_unique_card_ids(document))
    for card in document.cards:
        issues.extend(_check_option_sets(card))
        issues.extend(_check_duplicate_options(card))
        issues.extend(_check_family_rules(card))
        issues.extend(_check_unresolved_review(card))
    return issues


def validate_for_export(
    document: CaptureIR, *, capabilities: set[str] | None = None
) -> list[Issue]:
    """Everything in ``validate_document`` plus the rules that only bind at export time.

    ``capabilities`` is the target's declared capability set. Multiple-select is blocked rather
    than degraded when the target cannot render it — BIBLE invariant 5, and the reason the live
    razbiram.com MCQ runtime (single-answer only) does not silently receive multi-answer cards.
    """
    issues = validate_document(document)
    declared = capabilities if capabilities is not None else set(document.target.capabilities)
    for card in document.cards:
        issues.extend(_check_answer_evidence(card))
        if card.family == "multiple-select" and "mcq.multiple-select.v1" not in declared:
            issues.append(
                Issue(
                    "capability-missing",
                    "target does not declare mcq.multiple-select.v1; the card is blocked, never "
                    "downgraded to single-choice",
                    card_id=card.cardId,
                )
            )
    return issues
