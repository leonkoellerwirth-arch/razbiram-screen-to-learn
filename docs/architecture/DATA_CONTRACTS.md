# Data contracts

## Contract layers

Do not make one JSON shape serve incompatible purposes.

| Layer | Purpose | Stability |
|---|---|---|
| `ingest-envelope.v1` | Normalized source/artifact declaration | public adapter contract |
| `extension-capture.v1` | Portable active-tab evidence manifest | public extension contract |
| Capture bundle | Browser evidence and artifacts | internal, versioned |
| `capture-ir.v1` | Lossless card semantics + field evidence + review | public tool contract |
| proposed `razbiram.recall-deck.v1` | Approved portable card semantics | family/hub-owned |
| Export profile | Exact target-deck representation | target-owned |
| Validation report | Compatibility, evidence, and rights findings | tool-owned |

## Capture IR

Top-level shape:

```json
{
  "schemaVersion": "capture-ir.v1",
  "sessionId": "ses_01...",
  "source": {
    "kind": "synthetic-fixture",
    "policy": "third-party-observe",
    "origin": "https://example.edu",
    "path": "/practice",
    "capturedAt": "2026-07-25T12:00:00Z"
  },
  "target": {
    "profile": "studywithme-bg.learncard.v1",
    "capabilities": ["mcq.single", "mcq.true-false", "matching", "typed", "flashcard", "image-occlusion"]
  },
  "deck": {
    "deckKey": "medical-biophysics-01",
    "bookKey": "medical-biophysics",
    "title": { "en": "Biophysics" },
    "description": { "en": "Reviewed practice cards." },
    "level": "medical",
    "difficulty": "intermediate",
    "languages": { "source": "en", "target": "en" },
    "tags": ["biophysics"]
  },
  "cards": []
}
```

### Common card fields

```json
{
  "draftId": "draft_sha256-prefix",
  "cardId": "q-0001",
  "sourceId": "src_sha256-prefix",
  "family": "single-choice",
  "prompt": {
    "value": { "en": "Question text" },
    "evidence": ["ev_question_dom", "ev_question_crop"],
    "confidence": 1.0
  },
  "review": {
    "status": "needs-review",
    "blockingReasons": [],
    "reviewedBy": null,
    "reviewedAt": null
  },
  "rights": {
    "basis": "unconfirmed",
    "licenseNotes": null,
    "approvedForPublication": false
  }
}
```

`confidence` helps prioritize review; it never substitutes for evidence.

### Evidence record

```json
{
  "evidenceId": "ev_question_dom",
  "kind": "dom|aria|screenshot-region|ocr|visible-feedback|reviewer",
  "captureId": "cap_sha256-prefix",
  "artifactId": "art_sha256-prefix",
  "region": { "x": 0.12, "y": 0.31, "width": 0.71, "height": 0.28 },
  "sourceRole": "question|option|answer-key|explanation|image",
  "authority": "content|user-selection|solution|reviewer",
  "sha256": "hex",
  "extractor": "dom-v1",
  "runId": "run_..."
}
```

Published decks contain at most an opaque/sanitized source reference. Raw evidence stays in a
private sidecar unless explicitly exported.

## Intake and extension contracts

`ingest-envelope.v1` gives every adapter the same immutable start point. Its `sourceKind` is one
of `browser-extension`, `controlled-browser`, `extension-bundle`, `image-upload`, `pdf-upload`,
`text-input`, or `synthetic-fixture`.

`extension-capture.v1` is the manifest inside `.razcapture` and the commit object used by paired
transfer. It declares:

- extension/browser/protocol versions;
- sanitized origin/path/title and viewport;
- `once`, `observe`, or `region` capture mode;
- semantic-snapshot capability;
- artifact IDs, roles, media types, byte sizes, and SHA-256 hashes;
- privacy flags such as stripped query and excluded form controls;
- question fingerprint when one can be computed deterministically.

Portable contracts contain no absolute local path, raw query string, fragment, cookie, provider
key, or executable captured markup. See the schemas and examples under `docs/schemas/`.

## Reviewed-deck projection

After approval, Capture IR projects into the proposed `razbiram.recall-deck.v1` family contract.
This contract does not exist in the hub yet; naming and schema require a `razbiram-nlp` Mini-ADR.
It is the intended boundary for sibling tools such as razbiram-anki.

The projection:

- includes reviewed card semantics, stable IDs, media hashes, evidence tier summary, and rights
  status;
- excludes screenshots, DOM/ARIA snapshots, browser paths, and the detailed review audit;
- blocks unresolved or unsupported cards;
- is deterministic for the same approved IR;
- does not replace target-specific capability checks.

Native Learn JSON and Anki exports are sibling projections. Neither is converted through the
other.

## Card families in Capture IR

### Single-choice

```json
{
  "family": "single-choice",
  "options": [
    { "optionId": "opt_a", "text": "A", "isCorrect": false, "evidence": ["ev_a"] },
    { "optionId": "opt_b", "text": "B", "isCorrect": true, "evidence": ["ev_b", "ev_key_b"] }
  ],
  "correctOptionIds": ["opt_b"],
  "answerEvidenceTier": "source-verified"
}
```

Invariant: exactly one correct option.

### Multiple-select

```json
{
  "family": "multiple-select",
  "options": [
    { "optionId": "opt_a", "text": "A", "isCorrect": true, "evidence": ["ev_a_key"] },
    { "optionId": "opt_b", "text": "B", "isCorrect": false, "evidence": ["ev_b_key"] },
    { "optionId": "opt_c", "text": "C", "isCorrect": true, "evidence": ["ev_c_key"] }
  ],
  "correctOptionIds": ["opt_a", "opt_c"],
  "scoring": { "mode": "all-or-nothing", "points": 1 },
  "answerEvidenceTier": "source-verified"
}
```

Invariants:

- options have stable unique IDs;
- `correctOptionIds` is a set and equals all `isCorrect: true` IDs;
- at least one option is correct;
- no semicolon-joined answer field represents the set;
- target export is blocked unless `mcq.multiple-select.v1` is available.

### True/false

```json
{
  "family": "true-false",
  "statement": {
    "value": { "en": "A photon has zero rest mass." },
    "evidence": ["ev_statement"]
  },
  "answer": true,
  "labels": { "true": "True", "false": "False" },
  "answerEvidenceTier": "source-verified"
}
```

The semantic source family is retained in the IR. The current compatibility exporter maps it to
an MCQ with exactly two options and one correct answer.

### Existing Razbiram families

The IR models existing target concepts directly:

- `matching`: `leftItems`, `rightItems`, `correctPairs`;
- `typed`: `acceptableAnswers`, optional `requiredKeywords`;
- `flashcard`: localized `front` and `back`;
- `image-occlusion`: base image artifact and reviewed region/mask data.

Do not invent alternate renderers. The exporter must follow the current live razbiram adapter
contract and M0 must round-trip a fixture for each family.

## Current compatibility export

Reference deck:
`app/studywithme-bg/learncards/Biophysics/deck-01.json`.

Required deck hull:

```json
{
  "schemaId": "studywithme-bg.learncard.v1",
  "deckKey": "biophysics-cybernatics-01",
  "bookKey": "biophysics-exam-preparation",
  "meta": {
    "title": { "en": "Title" },
    "description": { "en": "Description" },
    "level": "medical",
    "tags": ["medical", "biophysics"],
    "difficulty": "intermediate",
    "estimatedMinutes": 25,
    "cardCount": 33,
    "languages": { "source": "en", "target": "en" },
    "source": {
      "kind": "browser-capture",
      "rightsBasis": "permission-confirmed"
    }
  },
  "cards": []
}
```

Although `estimatedMinutes` and `cardCount` are currently derivable in the loader, the exporter
writes correct explicit values.

### Single-choice output

```json
{
  "cardId": "q-0001",
  "type": "mcq",
  "sourceId": "src_...",
  "question": { "en": "Information is:" },
  "correctAnswer": "any set of related data",
  "options": [
    { "text": "the transmitted message", "isCorrect": false },
    { "text": "any set of related data", "isCorrect": true }
  ],
  "scoring": { "mode": "single-best-answer", "points": 1 }
}
```

`correctAnswer` must exactly equal the correct option's `text`.

### True/false compatibility output

```json
{
  "cardId": "q-0002",
  "type": "mcq",
  "sourceFormat": "true-false",
  "question": { "en": "A photon has zero rest mass." },
  "correctAnswer": "True",
  "options": [
    { "text": "True", "isCorrect": true },
    { "text": "False", "isCorrect": false }
  ],
  "scoring": { "mode": "single-best-answer", "points": 1 }
}
```

The current renderer can present this as a radiogroup. The target validator must allow exactly
two options when `sourceFormat` is `true-false`.

### Multiple-select target extension

The existing runtime is not safe for multiple-select. The coordinated additive proposal is:

```json
{
  "cardId": "q-0003",
  "type": "mcq",
  "selectionMode": "multiple",
  "question": { "en": "Select all correct statements." },
  "options": [
    { "optionId": "opt_a", "text": "A", "isCorrect": true },
    { "optionId": "opt_b", "text": "B", "isCorrect": false },
    { "optionId": "opt_c", "text": "C", "isCorrect": true }
  ],
  "correctOptionIds": ["opt_a", "opt_c"],
  "scoring": { "mode": "all-or-nothing", "points": 1 }
}
```

This shape is a proposal, not an active production promise. The final identifier/shape belongs in
a coordinated razbiram.com schema decision. Before that decision, multiple-select remains valid
Capture IR but `exportable: false` for this target.

## Config output

Use `accessTier`, not the legacy/drifted `access` key:

```json
{
  "topicKey": "biophysics-practice-first-year",
  "accessTier": "premium",
  "year": "1",
  "semester": "2",
  "title": { "en": "Biophysics Practice" },
  "description": { "en": "Reviewed practice decks." },
  "decks": {
    "biophysics-cybernatics-01": {
      "description": { "en": "Cybernetics practice." },
      "estimatedMinutes": 25,
      "difficulty": "intermediate",
      "tags": ["biophysics"],
      "visible": true
    }
  }
}
```

## Stable IDs

- `sessionId`: random ULID; operational only.
- `captureId`: SHA-256 of normalized capture manifest plus artifact hashes.
- `sourceId`: SHA-256 of source scope + question fingerprint.
- `optionId`: stable hash of source ID + source option identity, not displayed text alone.
- `cardId`: deterministic per approved deck ordering or stable source ID mapping.
- `deckKey`: reviewer-approved URL-safe slug; stable across reruns.

Changing formatting must not remint semantic IDs.

## Blocking validation

- schema and declared version valid;
- supported target card family/capability;
- unique IDs;
- non-empty required languages;
- `meta.cardCount === cards.length`;
- Single-choice: exactly one correct and exact answer/option equality;
- Multiple-select: set equality and target capability;
- True/false: boolean answer and exactly two labels/options;
- Matching: referential integrity and unique item IDs;
- Typed: at least one acceptable answer;
- Flashcard: non-empty front/back;
- Image-occlusion: media exists, hash matches, regions and alt text valid;
- answer evidence tier is `source-verified` or `reviewer-confirmed`;
- no unresolved review blockers;
- rights decision is present for publication;
- final size/card limits respected.

## Warnings

- low OCR/model confidence;
- duplicated normalized option text;
- unusually long prompt/option;
- missing optional rationale/hint;
- question assembled across scroll captures;
- user-selection is the only observed answer signal;
- detected source inconsistency preserved with a `validationNote`.
