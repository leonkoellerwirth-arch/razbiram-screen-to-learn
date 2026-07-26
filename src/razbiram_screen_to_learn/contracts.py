"""Typed Python view of ``capture-ir.v1``.

The committed JSON Schema in ``docs/schemas/`` is the wire contract: it is what validates a
document arriving from the extension or from disk. These models are the typed view the pipeline
works with. The two must agree, which ``tests/test_contracts.py`` asserts by round-tripping the
committed example; they are not expected to be byte-identical, because a generated schema never
reproduces a hand-written one exactly.

``extra="forbid"`` mirrors ``unevaluatedProperties: false`` in the schema and follows the family
convention in razbiram-nlp: contract drift should be loud.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "capture-ir.v1"

CardFamily = Literal[
    "single-choice",
    "multiple-select",
    "true-false",
    "matching",
    "typed",
    "flashcard",
    "image-occlusion",
]
SourceKind = Literal[
    "browser-extension",
    "controlled-browser",
    "extension-bundle",
    "image-upload",
    "pdf-upload",
    "text-input",
    "synthetic-fixture",
]
SourcePolicy = Literal[
    "user-upload", "first-party-owned", "permission-confirmed", "third-party-observe"
]
ReviewStatus = Literal["needs-review", "approved", "rejected"]
RightsBasis = Literal[
    "user-authored",
    "licensed",
    "public-domain",
    "permission-confirmed",
    "personal-use-unconfirmed",
    "unconfirmed",
]
ScoringMode = Literal["single-best-answer", "all-or-nothing", "partial-credit"]
EvidenceTier = Literal[
    "source-verified", "reviewer-confirmed", "source-ambiguous", "model-inferred", "unknown"
]
EvidenceKind = Literal["dom", "aria", "screenshot-region", "ocr", "visible-feedback", "reviewer"]
SourceRole = Literal["question", "option", "answer-key", "explanation", "image"]
Authority = Literal["content", "user-selection", "solution", "reviewer"]
Difficulty = Literal["beginner", "intermediate", "advanced"]

#: Only these two tiers may reach export. See PIPELINE.md "Correctness tiers".
EXPORTABLE_TIERS: frozenset[str] = frozenset({"source-verified", "reviewer-confirmed"})

LocalizedText = dict[str, str]
NonEmptyStr = Annotated[str, Field(min_length=1)]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(_Frozen):
    kind: SourceKind
    policy: SourcePolicy
    origin: str
    path: str
    capturedAt: str


class Target(_Frozen):
    profile: NonEmptyStr
    capabilities: list[str]


class Deck(_Frozen):
    deckKey: NonEmptyStr
    bookKey: str | None = None
    title: LocalizedText
    description: LocalizedText
    level: NonEmptyStr
    difficulty: Difficulty
    languages: dict[str, str]
    tags: list[str]


class Evidence(_Frozen):
    evidenceId: NonEmptyStr
    kind: EvidenceKind
    captureId: NonEmptyStr
    artifactId: str | None = None
    sourceRole: SourceRole
    authority: Authority
    sha256: str | None = None
    extractor: NonEmptyStr
    runId: NonEmptyStr


class Field_(_Frozen):
    """A localized value carrying its own evidence and confidence."""

    value: LocalizedText
    evidence: list[str]
    confidence: float


class Option(_Frozen):
    optionId: NonEmptyStr
    text: str
    isCorrect: bool
    evidence: list[str]


class Review(_Frozen):
    status: ReviewStatus
    blockingReasons: list[str]
    reviewedBy: str | None = None
    reviewedAt: str | None = None


class Rights(_Frozen):
    basis: RightsBasis
    licenseNotes: str | None = None
    approvedForPublication: bool


class Scoring(_Frozen):
    mode: ScoringMode
    points: float


class Card(_Frozen):
    draftId: NonEmptyStr
    cardId: NonEmptyStr
    sourceId: NonEmptyStr
    family: CardFamily
    prompt: Field_
    review: Review
    rights: Rights
    answerEvidenceTier: EvidenceTier | None = None

    # Family-specific. Presence is enforced by the schema's discriminated branches and re-checked
    # by validate_document(); modelling them as optional keeps one class per contract object.
    options: list[Option] | None = None
    correctOptionIds: list[str] | None = None
    scoring: Scoring | None = None
    statement: Field_ | None = None
    answer: bool | None = None
    labels: dict[str, str] | None = None
    leftItems: list[dict] | None = None
    rightItems: list[dict] | None = None
    correctPairs: list[dict] | None = None
    acceptableAnswers: list[str] | None = None
    requiredKeywords: list[str] | None = None
    front: Field_ | None = None
    back: Field_ | None = None
    baseImageArtifactId: str | None = None
    occlusionRegions: list[dict] | None = None


class CaptureIR(_Frozen):
    schemaVersion: Literal["capture-ir.v1"] = SCHEMA_VERSION
    sessionId: NonEmptyStr
    source: Source
    target: Target
    deck: Deck
    evidence: list[Evidence] = Field(default_factory=list)
    cards: list[Card] = Field(default_factory=list)


def dump_document(document: CaptureIR) -> dict:
    """Serialize to the exact JSON shape the committed schema expects.

    ``exclude_none`` is wrong here and ``exclude_unset`` alone is not enough. Several fields are
    *required but nullable* (``review.reviewedBy``, ``review.reviewedAt``, ``rights.licenseNotes``)
    and must be emitted as ``null``, while the family-specific fields must be absent rather than
    ``null`` on families that do not use them. ``exclude_unset`` gets both right, since an
    explicitly-passed ``None`` counts as set — it only drops ``schemaVersion``, which carries a
    default and is therefore restored here.

    Every producer goes through this function so the API, the CLI and the tests cannot drift.
    """
    payload = document.model_dump(mode="json", exclude_unset=True)
    payload["schemaVersion"] = document.schemaVersion
    return payload
