"""One call from an intake file to a validated, capability-gated export.

This is the M0 vertical slice: Intake -> Extract -> Validate -> Export. The stages named in
``docs/architecture/PIPELINE.md`` exist as separate modules; this facade wires the subset M0
implements so the CLI and the studio API share exactly one code path.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from razbiram_screen_to_learn.contracts import (
    CaptureIR,
    Card,
    Deck,
    Evidence,
    EvidenceKind,
    Source,
    SourceKind,
    Target,
)
from razbiram_screen_to_learn.export import TARGET_PROFILE, ExportResult, export_deck
from razbiram_screen_to_learn.extract import extract_document
from razbiram_screen_to_learn.identity import capture_id as derive_capture_id
from razbiram_screen_to_learn.progress import (
    STAGE_EXPORTING,
    STAGE_SEGMENTING,
    STAGE_VALIDATING,
    ProgressEvent,
    ProgressFn,
    report,
)
from razbiram_screen_to_learn.textcards import build_card
from razbiram_screen_to_learn.textseg import RawBlock, segment
from razbiram_screen_to_learn.validators import Issue, validate_for_export

#: The card formats the target engine can parse, read from a pinned copy of the profile
#: razbiram.com publishes at ``/learncards/profile.v1.json``.
#:
#: The integration boundary is the deck JSON and nothing else, so a "capability" names a *format
#: the engine can parse*, not a feature anyone builds for this tool.
#:
#: Deliberately a committed file rather than a live fetch, which is what the cross-repo plan
#: proposed. Two reasons: this tool is local-first and must export with no network at all, and a
#: Golden run whose result depends on a remote file is not deterministic. Refreshing the copy is an
#: explicit, reviewable act (``scripts/refresh-target-profile.sh``), so a capability can never
#: change under an export without someone seeing the diff.
PROFILE_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "schemas" / "learncard-target.profile.v1.json"
)


def _load_capabilities() -> frozenset[str]:
    try:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A missing or broken profile must not silently widen what we export. Nothing declared
        # means nothing beyond the single-answer baseline leaves the tool.
        return frozenset({"mcq.single"})
    declared = profile.get("capabilities")
    if not isinstance(declared, list) or not all(isinstance(c, str) for c in declared):
        return frozenset({"mcq.single"})
    return frozenset(declared)


LIVE_CAPABILITIES: frozenset[str] = _load_capabilities()

DEFAULT_DECK = Deck(
    deckKey="fixture-demo-01",
    bookKey="fixture-demo",
    title={"en": "Fixture demo"},
    description={"en": "Cards extracted from the synthetic fixture."},
    level="general",
    difficulty="intermediate",
    languages={"source": "en", "target": "en"},
    tags=["fixture"],
)


@dataclass
class PipelineResult:
    document: CaptureIR
    issues: list[Issue]
    export: ExportResult
    unsupported: list[str]
    #: Set by the text path: the raw text intake worked from, so a caller can show what was read.
    text: str | None = None


def _text_deck(title: str, locale: str) -> Deck:
    """A deck for material a person supplied, rather than the built-in fixture.

    ``languages`` is part of the target schema, so it must be filled — but this tool does not
    classify anyone's material, so it says ``und`` (ISO 639-2 "undetermined") rather than guess.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "captured"
    # Truncating can land on a hyphen, and "…eight--5d8c5119" fails the schema's deckKey pattern.
    stem = slug[:40].rstrip("-") or "captured"
    return Deck(
        deckKey=f"{stem}-{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}",
        bookKey=None,
        title={locale: title},
        description={locale: "Extracted from supplied material."},
        level="general",
        difficulty="intermediate",
        languages={"source": locale, "target": locale},
        tags=["captured"],
    )


def process_text(
    text: str,
    *,
    title: str = "Captured deck",
    source_kind: SourceKind = "text-input",
    evidence_kind: EvidenceKind = "ocr",
    origin: str = "file://local",
    path: str = "/upload",
    captured_at: str = "1970-01-01T00:00:00Z",
    session_id: str = "ses_local",
    run_id: str = "run_local",
    capabilities: frozenset[str] | set[str] = LIVE_CAPABILITIES,
    locale: str = "und",
    on_progress: ProgressFn | None = None,
) -> PipelineResult:
    """Run the M0 slice over plain text — the OCR, PDF and paste path.

    Segmentation and family detection are deterministic (``textseg``/``textcards``); nothing here
    invents a correct answer. As in the DOM path, ``captured_at`` is a parameter, not a clock read,
    so identical input yields identical identifiers.
    """
    blocks, answer_key = segment(text)
    return _assemble(
        blocks,
        answer_key,
        text=text,
        title=title,
        source_kind=source_kind,
        evidence_kind=evidence_kind,
        origin=origin,
        path=path,
        captured_at=captured_at,
        session_id=session_id,
        run_id=run_id,
        capabilities=capabilities,
        locale=locale,
        on_progress=on_progress,
    )


def _assemble(
    blocks: list[RawBlock],
    answer_key: dict[int, list[str]],
    *,
    text: str | None,
    title: str,
    source_kind: SourceKind,
    evidence_kind: EvidenceKind,
    origin: str,
    path: str,
    captured_at: str,
    session_id: str,
    run_id: str,
    capabilities: frozenset[str] | set[str],
    locale: str,
    on_progress: ProgressFn | None,
) -> PipelineResult:
    """Turn segmented blocks into a validated, capability-gated result.

    Shared by every intake: whether the blocks came from letters in the text or from typography
    and colour in a screenshot, what happens to them afterwards must be identical.
    """
    capture = derive_capture_id(
        created_at=captured_at,
        origin=origin,
        path=path,
        capture_state="question",
        question_fp="0" * 64,
        artifact_hashes=[],
    )
    target = Target(profile=TARGET_PROFILE, capabilities=sorted(capabilities))
    cards: list[Card] = []
    evidence: list[Evidence] = []
    unsupported: list[str] = []

    # Countable from here on: the blocks are known, so the remaining work has a real denominator.
    report(
        on_progress,
        ProgressEvent(
            stage=STAGE_SEGMENTING,
            detail=f"Found {len(blocks)} question block(s)",
            index=0,
            total=len(blocks),
        ),
    )

    for position, block in enumerate(blocks, start=1):
        built = build_card(
            block,
            answer_key,
            origin=origin,
            path=path,
            capture_id=capture,
            run_id=run_id,
            evidence_kind=evidence_kind,
            locale=locale,
        )
        report(
            on_progress,
            ProgressEvent(
                stage=STAGE_SEGMENTING,
                detail=f"Building card {position} of {len(blocks)}",
                index=position,
                total=len(blocks),
            ),
        )
        if built.card is None:
            unsupported.append(f"block-{built.question_index}")
            continue
        cards.append(built.card)
        evidence.extend(built.evidence)

    document = CaptureIR(
        sessionId=session_id,
        source=Source(
            kind=source_kind,
            policy="first-party-owned",
            origin=origin,
            path=path,
            capturedAt=captured_at,
        ),
        target=target,
        deck=_text_deck(title, locale),
        evidence=evidence,
        cards=cards,
    )
    report(on_progress, ProgressEvent(stage=STAGE_VALIDATING, detail="Checking the cards"))
    issues = validate_for_export(document, capabilities=set(capabilities))
    report(on_progress, ProgressEvent(stage=STAGE_EXPORTING, detail="Building the deck"))
    result = export_deck(document, capabilities=set(capabilities))
    return PipelineResult(
        document=document,
        issues=issues,
        export=result,
        unsupported=unsupported,
        text=text,
    )


def usable_blocks(blocks: list[RawBlock]) -> int:
    """How many blocks are actually answerable. The score a strategy is judged by."""
    return sum(1 for block in blocks if len(block.option_lines) >= 2 and block.question_lines)


def process_image(
    data: bytes,
    suffix: str,
    *,
    title: str = "Captured deck",
    locale: str = "und",
    capabilities: frozenset[str] | set[str] = LIVE_CAPABILITIES,
    on_progress: ProgressFn | None = None,
    **assemble_kwargs: object,
) -> PipelineResult:
    """Read an image, choosing between the two ways a page can carry its structure.

    Material that marks itself with letters ("A)", "B)") is read from the recognised text.
    Material that marks itself by drawing — a bigger question, a widget per choice, a tinted
    correct row — is read from typography, geometry and colour. Which applies is decided by
    **counting answerable blocks**, not by guessing from the file, so a page that carries both
    simply wins twice and a page that carries neither reports nothing rather than inventing it.
    """
    from razbiram_screen_to_learn.ocr import recognize_image
    from razbiram_screen_to_learn.screenshot import blocks_from_image

    recognised = recognize_image(data, suffix, on_progress=on_progress)
    text_blocks, answer_key = segment(recognised.text)

    drawn_blocks: list[RawBlock] = []
    with suppress(Exception):
        # A drawn page is the harder case; failing to read it must not lose the text reading.
        drawn_blocks, _ = blocks_from_image(data, suffix)

    if usable_blocks(drawn_blocks) > usable_blocks(text_blocks):
        blocks, answer_key = drawn_blocks, {}
    else:
        blocks = text_blocks

    return _assemble(
        blocks,
        answer_key,
        text=recognised.text,
        title=title,
        source_kind="image-upload",
        evidence_kind="ocr",
        origin=str(assemble_kwargs.get("origin", "file://local")),
        path=str(assemble_kwargs.get("path", "/upload")),
        captured_at=str(assemble_kwargs.get("captured_at", "1970-01-01T00:00:00Z")),
        session_id=str(assemble_kwargs.get("session_id", "ses_local")),
        run_id=str(assemble_kwargs.get("run_id", "run_local")),
        capabilities=capabilities,
        locale=locale,
        on_progress=on_progress,
    )


def process_markup(
    markup: str,
    *,
    origin: str = "https://fixture.local",
    path: str = "/fixture.html",
    captured_at: str = "1970-01-01T00:00:00Z",
    session_id: str = "ses_local",
    run_id: str = "run_local",
    capabilities: frozenset[str] | set[str] = LIVE_CAPABILITIES,
    deck: Deck | None = None,
) -> PipelineResult:
    """Run the M0 slice over one HTML document.

    ``captured_at`` is a parameter rather than a clock read so that the same input yields the same
    identifiers on every run — GOLDEN_SET.md requires deterministic output.
    """
    capture = derive_capture_id(
        created_at=captured_at,
        origin=origin,
        path=path,
        capture_state="question",
        question_fp="0" * 64,
        artifact_hashes=[],
    )
    target = Target(profile=TARGET_PROFILE, capabilities=sorted(capabilities))

    extraction = extract_document(
        markup,
        origin=origin,
        path=path,
        session_id=session_id,
        run_id=run_id,
        capture_id=capture,
        deck=deck or DEFAULT_DECK,
        target=target,
        captured_at=captured_at,
    )
    document = extraction.document
    issues = validate_for_export(document, capabilities=set(capabilities))
    result = export_deck(document, capabilities=set(capabilities))
    return PipelineResult(
        document=document,
        issues=issues,
        export=result,
        unsupported=extraction.unsupported,
    )
