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
- `captureState` (`question`, `reveal`, or `unknown`) — which role the capture plays in the join;
- `questionFingerprint` (the join key) and `stateFingerprint` (the per-state dedup key).

All three identity fields are required. The Join stage therefore groups and selects from the
manifest alone and never parses an artifact to find out what it is holding. A capture that cannot
be classified is emitted as `unknown` and routed to review rather than dropped.

Portable contracts contain no absolute local path, raw query string, fragment, cookie, provider
key, or executable captured markup. The semantic snapshot referenced by a capture has its own
contract in `semantic-snapshot.v1`; region geometry lives there under `capturedRegion`. See the
schemas and examples under `docs/schemas/`.

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
`studywithme_db/app/studywithme-bg/learncards/Biophysics/deck-01.json`.

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

`meta.source` in the hull above is the proposed output shape for new screen-to-learn exports.
Shipped decks may carry import-provenance instead, e.g.
`{"file": "deck.json", "book": "...", "originalDeckName": "..."}`.
The deck validator must accept both shapes; do not reject a deck solely because `meta.source`
lacks `kind`/`rightsBasis`.

Although `estimatedMinutes` and `cardCount` are currently derivable in the loader, the exporter
writes correct explicit values.

### Verified against live files

The following were confirmed against the live reference deck and razbiram.com runtime and must
not be re-litigated without new evidence:

- `schemaId: "studywithme-bg.learncard.v1"` is the active identifier in shipped decks.
- The single-choice output shape below is correct; `correctAnswer` is a singular string.
- `scoring.mode: "single-best-answer"` is what shipped decks use.
- `meta.cardCount: 33` matches the 33 real cards in the reference deck.
- razbiram.com's MCQ runtime is single-answer at every layer (`role="radiogroup"`,
  `correctAnswer?: string`, validator rejects more than one correct option); the
  multiple-select capability gate is therefore justified.

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

`access` is the live top-level key in shipped config files (`biophysics/config.json` and
peers). `accessTier` was a proposed migration target; it does not appear in any current config
and has not been adopted by the razbiram.com config loader. Verify against the loader before
writing it. Until that migration is confirmed, the exporter must write `access`; writing both
keys is acceptable as a transition aid.

The live config shape also carries `typedAnswerEvaluation`. The exporter must include this key
when the target deck covers a subject that requires evaluation hints:

```json
{
  "topicKey": "biophysics-practice-first-year",
  "access": "premium",
  "year": "1",
  "semester": "2",
  "title": { "en": "Biophysics Practice" },
  "description": { "en": "Reviewed practice decks." },
  "typedAnswerEvaluation": {
    "subject": "biophysics",
    "domain": "physics in medicine",
    "allowCrossLanguageEquivalence": false,
    "requireTerminologyPrecision": true,
    "requireUnitPrecision": true,
    "requireFormulaPrecision": true,
    "evaluatorNotes": [
      "Require correct physical laws, variable meaning, units, and symbolic relations.",
      "Reject sign errors, reversed dependencies, and quantitatively wrong statements."
    ]
  },
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

`docs/architecture/IDENTITY_ALGORITHMS.md` is authoritative for the exact normalization,
serialization, and hashing of every derived identifier. The summary below must not diverge from it.

- `sessionId`: random ULID; operational only.
- `captureId`: SHA-256 of normalized capture manifest plus artifact hashes.
- `sourceId`: `src_` + first 32 hex of SHA-256 over source scope and `questionFingerprint`.
- `optionId`: `opt_` + first 32 hex of SHA-256 over source ID and the option's normalized
  `cleanText` — never displayed text alone.
- `cardId` **in Capture IR**: `q-` + first 16 hex of SHA-256 over the source ID. Source-stable and
  independent of reviewer ordering.
- `deckKey`: reviewer-approved URL-safe slug; stable across reruns.

Changing formatting must not remint semantic IDs.

### Card identity across the IR/export boundary

The IR identifier and the exported deck identifier are deliberately different, because they answer
different questions.

| Layer | Field | Form | Why |
|---|---|---|---|
| Capture IR | `cardId` | `q-<16 hex>` | Canonical identity; survives reordering, re-capture, and review |
| Export deck | `cardId` | `q-0001` … | Sequential label; matches every shipped deck |
| Export deck | `sourceId` | `src_<32 hex>` | Carries the stable identity into the product |

Verified against the live reference deck: its cards run `q-0001` … `q-0033` **and** every card
already carries a `sourceId`. razbiram.com's validator only requires a non-empty `cardId`
(`deckSchema.ts:139`), so it does not constrain the form — but shipped decks are sequential, and
the exporter matches them. Stable cross-export identity therefore travels in `sourceId`, which the
product already stores, rather than in a re-minted `cardId`.

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

### Cross-field validators (code responsibility, not schema)

JSON Schema cannot enforce the following invariants. They are explicit code-validator
responsibilities:

- `correctOptionIds` equals the set of option IDs where `isCorrect` is `true`.
- `meta.cardCount === cards.length`.
- Evidence referential integrity: every `evidenceId` referenced in any card field exists in
  the top-level `evidence` ledger.
- Single-choice: `correctAnswer` in the export exactly equals the correct option's `text`.
- True/false: exactly two options (one `True`, one `False`).
- Matching: every `leftItemId` and `rightItemId` in `correctPairs` exists in `leftItems`/
  `rightItems`; item IDs are unique within each side.
- Typed: `acceptableAnswers` has at least one non-empty entry.
- Image-occlusion: base image artifact exists and its hash matches the declared hash; each
  occlusion region has non-empty `altText`.

## Warnings

- low OCR/model confidence;
- duplicated normalized option text;
- unusually long prompt/option;
- missing optional rationale/hint;
- question assembled across scroll captures;
- user-selection is the only observed answer signal;
- detected source inconsistency preserved with a `validationNote`.
