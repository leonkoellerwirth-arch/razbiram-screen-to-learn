"""One call from an intake file to a validated, capability-gated export.

This is the M0 vertical slice: Intake -> Extract -> Validate -> Export. The stages named in
``docs/architecture/PIPELINE.md`` exist as separate modules; this facade wires the subset M0
implements so the CLI and the studio API share exactly one code path.
"""

from __future__ import annotations

from dataclasses import dataclass

from razbiram_screen_to_learn.contracts import CaptureIR, Deck, Target
from razbiram_screen_to_learn.export import TARGET_PROFILE, ExportResult, export_deck
from razbiram_screen_to_learn.extract import extract_document
from razbiram_screen_to_learn.identity import capture_id as derive_capture_id
from razbiram_screen_to_learn.validators import Issue, validate_for_export

#: What the live razbiram.com runtime can actually render today. Verified against its MCQ
#: component, its LearnCard type and its deck validator: single answer only, 3-5 options.
LIVE_CAPABILITIES: frozenset[str] = frozenset(
    {"mcq.single", "matching", "typed", "flashcard", "image-occlusion"}
)

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
