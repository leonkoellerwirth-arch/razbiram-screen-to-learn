"""Answer binding and family detection for text intake, then Capture IR cards.

Binding and detection live in ONE module on purpose: the family depends on how many answers were
evidenced, and the answers are resolved against the options. A port of razbiram.com's
``app/src/lib/ingest/classify.ts``, emitting this repo's ``capture-ir.v1`` contracts instead of a
razbiram deck, so the OCR/PDF/text path converges with the DOM path (BIBLE, dual intake).

THE RULE THIS FILE EXISTS TO ENFORCE: correctness is READ, never inferred. Material that carries
no answer key yields a card with no correct option, tier ``source-ambiguous`` — which the export
gate then refuses until a human confirms it (invariants 1 and 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import (
    Authority,
    Card,
    Evidence,
    EvidenceKind,
    Field_,
    Option,
    Review,
    Rights,
    Scoring,
    SourceRole,
)
from razbiram_screen_to_learn.identity import (
    card_id,
    clean_text,
    option_id,
    question_fingerprint,
    source_id,
)
from razbiram_screen_to_learn.quality import fold_homoglyphs, readability
from razbiram_screen_to_learn.textseg import AnswerKey, RawBlock, block_question_text

EXTRACTOR = "text-v1"

#: Explicit multi-answer instructions. One of these decides the family outright.
MULTI_HINT_RE = re.compile(
    r"select\s+all|all\s+that\s+apply|choose\s+all|mark\s+all|w[aä]hle[n]?\s+(?:sie\s+)?alle"
    r"|mehrere\s+antworten|alle\s+zutreffenden|изберете\s+всички|отбележете\s+всички"
    r"|повече\s+от\s+един",
    re.IGNORECASE,
)

#: A two-option question is true/false ONLY if its options read as a true/false pair — never
#: because it happens to have two options (invariant 4: the shape is never inferred from a count).
TRUE_FALSE_PAIRS: tuple[tuple[str, str], ...] = (
    ("true", "false"),
    ("wahr", "falsch"),
    ("richtig", "falsch"),
    ("вярно", "невярно"),
    ("верно", "невярно"),
)

LATIN_IDS = "abcdefghijklmnopqrstuvwxyz"

#: Cyrillic letters that are visually identical to a Latin one. OCR picks whichever script its
#: loaded models favour, so a key can read "А,С" (Cyrillic) while the options read "A)" "C)"
#: (Latin) — the same glyphs, different code points, and no binding without folding them.
CYRILLIC_TO_LATIN = {
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Н": "H",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Т": "T",
    "Х": "X",
}
LATIN_TO_CYRILLIC = {latin: cyr for cyr, latin in CYRILLIC_TO_LATIN.items()}

#: Cyrillic letters with no Latin lookalike. One of these among the option markers proves the
#: document numbers its options in Cyrillic — decisive, because Bulgarian material runs
#: А, Б, В, Г, where "В" is the THIRD option and folding it to Latin "B" would bind the second.
CYRILLIC_ONLY = set("БГДЖЗИЙЛПУФЦЧШЩЪЬЮЯ")


def fold_letters(letters: list[str], markers: list[str]) -> list[str]:
    """Rewrite answer-key letters into the alphabet the option markers actually use."""
    to_cyrillic = any(marker in CYRILLIC_ONLY for marker in markers)
    table = LATIN_TO_CYRILLIC if to_cyrillic else CYRILLIC_TO_LATIN
    return [table.get(letter, letter) for letter in letters]


def _norm(value: str) -> str:
    return re.sub(r"[.!?]+$", "", value.lower()).strip()


def is_true_false_pair(texts: list[str]) -> bool:
    if len(texts) != 2:
        return False
    a, b = _norm(texts[0]), _norm(texts[1])
    return any((a == t and b == f) or (a == f and b == t) for t, f in TRUE_FALSE_PAIRS)


@dataclass(frozen=True)
class AnswerResolution:
    letters: list[str]
    #: Where correctness came from. "none" means the material never declared it.
    source: str


def resolve_answers(block: RawBlock, answer_key: AnswerKey) -> AnswerResolution:
    """Resolve which option letters the material declares correct.

    Priority: an explicit "Answer: B" line, then a trailing answer-key row, then inline marks.
    """
    if block.inline_answers:
        return AnswerResolution(letters=block.inline_answers, source="inline")

    from_key = answer_key.get(block.index)
    if from_key:
        return AnswerResolution(letters=from_key, source="answer-key")

    marked = [
        line.marker or LATIN_IDS[i].upper()
        for i, line in enumerate(block.option_lines)
        if line.marked and i < len(LATIN_IDS)
    ]
    if marked:
        return AnswerResolution(letters=marked, source="inline-mark")

    return AnswerResolution(letters=[], source="none")


def detect_family(question_text: str, option_texts: list[str], correct_count: int) -> str:
    """What kind of question this is — decided from the material, never from the option count.

    Whether the answer is *known* has no bearing on the shape: a true/false question printed
    without its key is still a true/false question, and calling it single-choice would lose the
    distinction the IR exists to preserve (invariant 4). What settles it is that the two options
    read as a true/false pair, which is a fact about the text.
    """
    if MULTI_HINT_RE.search(question_text):
        return "multiple-select"
    if correct_count > 1:
        return "multiple-select"
    if is_true_false_pair(option_texts):
        return "true-false"
    return "single-choice"


@dataclass
class BlockCard:
    """A built card plus the evidence rows it produced and why it may need review."""

    card: Card | None
    evidence: list[Evidence]
    review_reasons: list[str]
    question_index: int


def build_card(
    block: RawBlock,
    answer_key: AnswerKey,
    *,
    origin: str,
    path: str,
    capture_id: str,
    run_id: str,
    evidence_kind: EvidenceKind,
    locale: str,
) -> BlockCard:
    """Turn one segmented block into a Capture IR card. Never invents an answer.

    ``locale`` keys every localized field. It is supplied by the caller rather than guessed here,
    because this tool does not classify anyone's material — see ``pipeline.process_text``.
    """
    question = block_question_text(block)
    resolution = resolve_answers(block, answer_key)
    markers = [(line.marker or "").upper() for line in block.option_lines]
    wanted = {letter.upper() for letter in fold_letters(resolution.letters, markers)}

    # Repair before judging: a word written half in Latin and half in Cyrillic is a recogniser
    # slip with an unambiguous fix, and folding it back costs a person nothing to review. Text that
    # is still damaged afterwards is reported rather than published — see the tier check below.
    texts = [fold_homoglyphs(clean_text(line.text)) for line in block.option_lines]

    # Report the block's actual defect. Blaming a missing answer key for a block that has no
    # question at all sends a reviewer looking for the wrong thing.
    if not question:
        return BlockCard(None, [], ["no-question-text"], block.index)
    if len(texts) < 2:
        return BlockCard(None, [], ["too-few-options"], block.index)

    review_reasons: list[str] = []
    if resolution.source == "none":
        review_reasons.append("no-answer-key")

    family_probe = [
        (block.option_lines[i].marker or LATIN_IDS[i].upper()) for i in range(len(texts))
    ]
    correct_flags = [
        marker.upper() in wanted or LATIN_IDS[i].upper() in wanted
        for i, marker in enumerate(family_probe)
    ]
    correct_count = sum(correct_flags)
    if resolution.source != "none" and correct_count == 0:
        review_reasons.append("answer-key-unresolved")

    family = detect_family(question, texts, correct_count)
    if family == "multiple-select" and correct_count < 2 and resolution.source != "none":
        # The question says "select all" but only one answer was evidenced — a human decides.
        review_reasons.append("ambiguous-family")

    fingerprint = question_fingerprint(
        origin=origin,
        path=path,
        card_family=family,
        question_text=question,
        option_texts=texts,
    )
    source = source_id(origin=origin, path=path, question_fp=fingerprint)

    evidence: list[Evidence] = []

    def record(suffix: str, role: SourceRole, authority: Authority) -> str:
        evidence_id = f"ev_{source[:16]}_{suffix}"
        evidence.append(
            Evidence(
                evidenceId=evidence_id,
                kind=evidence_kind,
                captureId=capture_id,
                sourceRole=role,
                authority=authority,
                extractor=EXTRACTOR,
                runId=run_id,
            )
        )
        return evidence_id

    prompt_evidence = record("stem", "question", "content")

    options: list[Option] = []
    for i, (text, is_correct) in enumerate(zip(texts, correct_flags, strict=True)):
        # Correctness is the source's own declaration, recorded with `solution` authority so the
        # evidence trail shows where it came from.
        authority = "solution" if is_correct else "content"
        options.append(
            Option(
                optionId=option_id(source=source, option_text=text),
                text=text,
                isCorrect=is_correct,
                evidence=[record(f"opt{i}", "option", authority)],
            )
        )

    # Only a declared answer key is source-verified. Without one the card must not reach export.
    tier = "source-verified" if correct_count > 0 else "source-ambiguous"

    # …and a declared answer we could not actually read is not an answer either. This is the check
    # that closes the failure class found on a real assessment: four of fourteen exported cards
    # carried a mangled correct option ("Therei h thi Sprint 0 in 5"), every one of them the tinted
    # row, and every one of them exported as source-verified because *something* was marked. Being
    # marked is not the same as being legible, and a learner drilled on an unreadable answer is
    # worse off than one shown no card at all.
    if tier == "source-verified":
        damaged = [
            verdict
            for option, verdict in ((o, readability(o.text)) for o in options if o.isCorrect)
            if not verdict.ok
        ]
        if damaged:
            tier = "source-ambiguous"
            review_reasons.append("unreadable-answer-text")
            review_reasons.extend(damaged[0].reasons)
    prompt = Field_(value={locale: question}, evidence=[prompt_evidence], confidence=1.0)
    review = Review(
        status="needs-review",
        blockingReasons=sorted(set(review_reasons)),
        reviewedBy=None,
        reviewedAt=None,
    )
    rights = Rights(basis="user-authored", licenseNotes=None, approvedForPublication=False)

    if family == "true-false":
        true_option = next(
            (o for o in options if _norm(o.text) in {t for t, _ in TRUE_FALSE_PAIRS}), options[0]
        )
        false_option = next((o for o in options if o is not true_option), options[1])
        card = Card(
            draftId=f"draft_{source[:24]}_true-false",
            cardId=card_id(source=source),
            sourceId=source,
            family="true-false",
            prompt=prompt,
            review=review,
            rights=rights,
            answerEvidenceTier=tier,
            statement=prompt,
            answer=true_option.isCorrect,
            labels={"true": true_option.text, "false": false_option.text},
        )
        return BlockCard(card, evidence, review_reasons, block.index)

    card = Card(
        draftId=f"draft_{source[:24]}_{family}",
        cardId=card_id(source=source),
        sourceId=source,
        family=family,
        prompt=prompt,
        review=review,
        rights=rights,
        answerEvidenceTier=tier,
        options=options,
        correctOptionIds=[o.optionId for o in options if o.isCorrect],
    )
    if family == "multiple-select":
        card = card.model_copy(update={"scoring": Scoring(mode="all-or-nothing", points=1.0)})
    return BlockCard(card, evidence, review_reasons, block.index)
