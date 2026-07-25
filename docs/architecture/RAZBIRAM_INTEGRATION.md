# razbiram integration

## Ownership boundary

`razbiram-screen-to-learn` owns:

- browser/file acquisition;
- extension capture, portable bundle, and local pairing contracts;
- evidence and provenance;
- card-family detection;
- extraction and review;
- compatibility validation;
- file/sidecar export.

`razbiram.com` owns:

- app-facing deck contracts;
- card renderers and interactions;
- scoring and learning-session semantics;
- content ingestion/catalog rules;
- progress and memory.

The tool must not create a parallel learning runtime.

`razbiram-anki` remains the owner of the Anki boundary. Screen-to-learn hands it only approved
portable deck semantics; it does not duplicate `.apkg` writing or route native Learn JSON through
CrowdAnki. See [RAZBIRAM_ANKI_BRIDGE.md](RAZBIRAM_ANKI_BRIDGE.md).

## Existing runtime reuse

Treat these as existing product capabilities:

- single-choice MCQ;
- matching;
- typed recall;
- flashcard;
- image occlusion.

The exporter maps to their live contract. M0 must build round-trip fixtures against the actual
product adapter and renderer because types alone do not prove that every field path agrees.

Only two runtime extensions are in scope:

### True/false

No new renderer is required. Export as single-choice MCQ with:

- two options;
- one correct answer;
- `sourceFormat: "true-false"` for provenance/editor semantics.

Required product change: allow a two-option MCQ in strict validators for this declared format.

### Multiple-select

Required product work:

1. additive, versioned contract/capability;
2. option IDs and `correctOptionIds`;
3. `Set<optionId>` selection state;
4. checkbox group semantics;
5. explicit Submit;
6. all-or-nothing scoring first;
7. correct/incorrect/missed feedback;
8. review/memory outcome semantics;
9. schema, adapter, unit, accessibility, and E2E tests.

Do not read current `scoring.mode: "multiple-select"` content as support. The current runtime
still selects one string and compares it with one correct string.

## Capability negotiation

The exporter uses a target manifest:

```json
{
  "target": "razbiram.com",
  "contract": "studywithme-bg.learncard.v1",
  "capabilities": {
    "mcq.single": true,
    "mcq.true-false": true,
    "mcq.multiple-select.v1": false,
    "matching": true,
    "typed": true,
    "flashcard": true,
    "image-occlusion": true
  },
  "limits": {
    "maxCards": 500,
    "maxJsonBytes": 524288
  }
}
```

Initially this is a version-controlled compatibility file backed by product tests. A live endpoint
is unnecessary for a local MVP.

## Export package

```text
export/
├── deck-01.json
├── config.json                 optional
├── media/                      only approved derived assets
├── validation-report.json
└── evidence-sidecar.json       optional, private, never catalog content
```

The UI promises **Download**. It does not claim direct upload or publication until a real product
route and authorization model are verified.

The export UI can additionally offer:

- **Download reviewed Razbiram deck** — the proposed family handoff contract;
- **Open in razbiram-anki** — exact-origin, user-initiated local handoff after file import works;
- **Download for Anki** — fulfilled by razbiram-anki only when its capability report is green.

## Schema strategy

The present app-facing legacy identifier stays unchanged for immediate compatibility. Do not
introduce a new `razbiram.*` identifier casually:

- tool-internal identifiers stay tool-scoped; a family identifier is assigned only by hub ADR;
- family contract identifiers and schema ownership belong to the shared hub;
- additive changes need tests and a Mini-ADR;
- a breaking runtime interpretation needs a major contract/version or an explicit minimum
  capability that old apps will reject safely.

The Capture IR is allowed to evolve independently because it is not directly rendered.

## Content repo integration

When a reviewed export is curated into the content repository:

1. place deck/media under the intended learncards topic;
2. create/update `config.json` with exact `deckKey`;
3. use `accessTier`;
4. validate JSON and referenced media;
5. verify `cardCount`;
6. run the product/content validators;
7. regenerate manifests only when their source content changed;
8. include validation report and rights review in the PR, not raw private screenshots.

The tool itself should not write into a sibling repo in MVP.

The extension may identify itself as a Razbiram tool and link voluntarily to razbiram.com. This
is a product-discovery surface, not a deck field or ingestion shortcut: no advertisement,
campaign metadata, forced attribution, or captured-content telemetry enters the export package.

## Provenance and originality

The proposed reviewed-deck contract must distinguish faithful extraction from original/generated
content. It does not exist yet, and the tool must never auto-assert originality for verbatim
screen or document extraction.

Separate:

- faithful personal extraction;
- permission/licensed publication;
- generated original practice aligned only to a curriculum structure.

Only the third can truthfully use an automatic original-content path, and even then requires
human review under the product policy.
