"""DOM-first extraction into ``capture-ir.v1``.

Content-first, per BIBLE invariant 2: structured DOM is read directly and vision/OCR is a later
fallback, not the primary path. This M0 extractor parses static HTML with the standard library, so
it runs offline and needs no browser. The Playwright-driven live-DOM path arrives with P5.6.

It never infers a correct answer. Correctness is read from the source's own answer key, and every
field carries the evidence record it came from.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import ClassVar

from razbiram_screen_to_learn.contracts import (
    CaptureIR,
    Card,
    Deck,
    Evidence,
    Field_,
    Option,
    Review,
    Rights,
    Scoring,
    Source,
    Target,
)
from razbiram_screen_to_learn.identity import (
    card_id,
    clean_text,
    normalize_text,
    option_id,
    question_fingerprint,
    source_id,
)

EXTRACTOR = "dom-v1"

#: Families this extractor can read from a static DOM. Others need the live-DOM or vision path and
#: are reported as unsupported rather than guessed at.
SUPPORTED_FAMILIES = frozenset({"single-choice", "multiple-select", "true-false", "flashcard"})


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[_Element] = field(default_factory=list)
    text: str = ""

    def find_all(self, predicate) -> list[_Element]:
        found = [self] if predicate(self) else []
        for child in self.children:
            found.extend(child.find_all(predicate))
        return found

    def text_content(self) -> str:
        parts = [self.text] + [child.text_content() for child in self.children]
        return " ".join(part for part in parts if part)


class _TreeBuilder(HTMLParser):
    """Minimal DOM builder. Void elements are not pushed, so the tree stays balanced."""

    VOID: ClassVar[frozenset[str]] = frozenset(
        {"area", "base", "br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("#document", {})
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag, {k: (v or "") for k, v in attrs})
        self._stack[-1].children.append(element)
        if tag not in self.VOID:
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack[-1].children.append(_Element(tag, {k: (v or "") for k, v in attrs}))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._stack[-1].children.append(_Element("#text", {}, text=data))


def parse_html(markup: str) -> _Element:
    builder = _TreeBuilder()
    builder.feed(markup)
    return builder.root


def _has_class(element: _Element, name: str) -> bool:
    return name in element.attrs.get("class", "").split()


def _draft_id(source: str, family: str) -> str:
    digest = hashlib.sha256(f"drf:1\nsource_id:{source}\nfamily:{family}".encode()).hexdigest()
    return "draft_" + digest[:16]


@dataclass
class ExtractionResult:
    document: CaptureIR
    unsupported: list[str]


def extract_document(
    markup: str,
    *,
    origin: str,
    path: str,
    session_id: str,
    run_id: str,
    capture_id: str,
    deck: Deck,
    target: Target,
    captured_at: str,
    source_kind: str = "synthetic-fixture",
    source_policy: str = "first-party-owned",
) -> ExtractionResult:
    """Extract every supported question container in ``markup`` into one Capture IR document."""
    root = parse_html(markup)
    containers = root.find_all(lambda e: "data-question-id" in e.attrs and "data-family" in e.attrs)

    evidence: list[Evidence] = []
    cards: list[Card] = []
    unsupported: list[str] = []

    def record(evidence_id: str, role: str, authority: str) -> str:
        evidence.append(
            Evidence(
                evidenceId=evidence_id,
                kind="dom",
                captureId=capture_id,
                sourceRole=role,
                authority=authority,
                extractor=EXTRACTOR,
                runId=run_id,
            )
        )
        return evidence_id

    for container in containers:
        family = container.attrs["data-family"]
        question_key = container.attrs["data-question-id"]
        if family not in SUPPORTED_FAMILIES:
            unsupported.append(question_key)
            continue

        card = _extract_card(
            container,
            family=family,
            question_key=question_key,
            origin=origin,
            path=path,
            record=record,
        )
        if card is None:
            unsupported.append(question_key)
        else:
            cards.append(card)

    document = CaptureIR(
        sessionId=session_id,
        source=Source(
            kind=source_kind,
            policy=source_policy,
            origin=origin,
            path=path,
            capturedAt=captured_at,
        ),
        target=target,
        deck=deck,
        evidence=evidence,
        cards=cards,
    )
    return ExtractionResult(document=document, unsupported=unsupported)


def _stem_text(container: _Element) -> str:
    stems = container.find_all(lambda e: _has_class(e, "question-stem"))
    return normalize_text(stems[0].text_content()) if stems else ""


def _option_elements(container: _Element) -> list[_Element]:
    return container.find_all(lambda e: _has_class(e, "option-item"))


def _option_text(item: _Element) -> str:
    labels = item.find_all(lambda e: "data-clean-text" in e.attrs)
    if labels:
        return labels[0].attrs["data-clean-text"]
    return item.text_content()


def _extract_card(
    container: _Element,
    *,
    family: str,
    question_key: str,
    origin: str,
    path: str,
    record,
) -> Card | None:
    stem = _stem_text(container)
    items = _option_elements(container)

    if family == "flashcard":
        return _extract_flashcard(
            container, question_key=question_key, origin=origin, path=path, record=record
        )

    if not items or not stem:
        return None

    texts = [_option_text(item) for item in items]
    fingerprint = question_fingerprint(
        origin=origin,
        path=path,
        card_family=family,
        question_text=stem,
        option_texts=texts,
    )
    source = source_id(origin=origin, path=path, question_fp=fingerprint)

    options: list[Option] = []
    for item, text in zip(items, texts, strict=True):
        cleaned = clean_text(text)
        is_correct = item.attrs.get("data-correct") == "true"
        # The answer key is the source's own declaration, never our inference. It is recorded with
        # `solution` authority so the evidence trail shows where correctness came from.
        authority = "solution" if is_correct else "content"
        evidence_id = record(f"ev_{question_key}_{cleaned[:24]}", "option", authority)
        options.append(
            Option(
                optionId=option_id(source=source, option_text=cleaned),
                text=cleaned,
                isCorrect=is_correct,
                evidence=[evidence_id],
            )
        )

    prompt_evidence = record(f"ev_{question_key}_stem", "question", "content")
    correct_ids = [option.optionId for option in options if option.isCorrect]

    if family == "true-false":
        # The IR keeps true/false as its own family rather than a two-option MCQ, so the semantic
        # source type survives to the exporter (BIBLE invariant 4).
        return _build_true_false(
            stem=stem,
            source=source,
            options=options,
            prompt_evidence=prompt_evidence,
        )

    card = Card(
        draftId=_draft_id(source, family),
        cardId=card_id(source=source),
        sourceId=source,
        family=family,
        prompt=Field_(value={"en": stem}, evidence=[prompt_evidence], confidence=1.0),
        review=Review(status="needs-review", blockingReasons=[], reviewedBy=None, reviewedAt=None),
        rights=Rights(basis="user-authored", licenseNotes=None, approvedForPublication=False),
        answerEvidenceTier="source-verified",
        options=options,
        correctOptionIds=correct_ids,
    )
    if family == "multiple-select":
        card = card.model_copy(update={"scoring": Scoring(mode="all-or-nothing", points=1.0)})
    return card


def _build_true_false(
    *, stem: str, source: str, options: list[Option], prompt_evidence: str
) -> Card | None:
    """Canonical true/false shape: a statement, a boolean answer, and the source's own labels.

    The labels are read from the page rather than hardcoded, so a source using "Richtig"/"Falsch"
    or "Yes"/"No" round-trips without being silently re-worded.
    """
    if len(options) != 2:
        return None
    true_option = next((o for o in options if clean_text(o.text).lower() == "true"), options[0])
    false_option = next((o for o in options if o is not true_option), options[1])
    return Card(
        draftId=_draft_id(source, "true-false"),
        cardId=card_id(source=source),
        sourceId=source,
        family="true-false",
        prompt=Field_(value={"en": stem}, evidence=[prompt_evidence], confidence=1.0),
        review=Review(status="needs-review", blockingReasons=[], reviewedBy=None, reviewedAt=None),
        rights=Rights(basis="user-authored", licenseNotes=None, approvedForPublication=False),
        answerEvidenceTier="source-verified",
        statement=Field_(value={"en": stem}, evidence=[prompt_evidence], confidence=1.0),
        answer=true_option.isCorrect,
        labels={"true": true_option.text, "false": false_option.text},
    )


def _extract_flashcard(
    container: _Element, *, question_key: str, origin: str, path: str, record
) -> Card | None:
    fronts = container.find_all(lambda e: _has_class(e, "flashcard-front"))
    backs = container.find_all(lambda e: _has_class(e, "flashcard-back"))
    if not fronts or not backs:
        return None

    front_text = normalize_text(fronts[0].text_content())
    back_text = normalize_text(backs[0].text_content())
    fingerprint = question_fingerprint(
        origin=origin,
        path=path,
        card_family="flashcard",
        question_text=front_text,
        option_texts=[],
    )
    source = source_id(origin=origin, path=path, question_fp=fingerprint)

    front_evidence = record(f"ev_{question_key}_front", "question", "content")
    back_evidence = record(f"ev_{question_key}_back", "answer-key", "solution")

    return Card(
        draftId=_draft_id(source, "flashcard"),
        cardId=card_id(source=source),
        sourceId=source,
        family="flashcard",
        prompt=Field_(value={"en": front_text}, evidence=[front_evidence], confidence=1.0),
        review=Review(status="needs-review", blockingReasons=[], reviewedBy=None, reviewedAt=None),
        rights=Rights(basis="user-authored", licenseNotes=None, approvedForPublication=False),
        answerEvidenceTier="source-verified",
        front=Field_(value={"en": front_text}, evidence=[front_evidence], confidence=1.0),
        back=Field_(value={"en": back_text}, evidence=[back_evidence], confidence=1.0),
    )
