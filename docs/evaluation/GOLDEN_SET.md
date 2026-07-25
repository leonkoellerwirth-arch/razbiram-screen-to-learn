# Golden-Set evaluation plan

## Purpose

The Golden-Set is the release gate for the core heuristic:

```text
owned/synthetic page, image, PDF, text, or extension state
→ ingest/capture
→ semantic extraction
→ evidence join
→ Capture IR
→ target export or expected block
```

CI runs without network. Real provider evaluations are opt-in `slow` jobs and cannot replace
deterministic fixtures.

## Fixture matrix

| ID | Fixture | Expected outcome |
|---|---|---|
| G01 | semantic radio single-choice + reveal | exact compatible MCQ |
| G02 | two-option true/false + reveal | exact compatible two-option MCQ |
| G03 | checkbox multiple-select + reveal | exact Capture IR; export blocked without capability |
| G04 | checkbox multiple-select with capability | exact IDs/set and compatible proposed export |
| G05 | matching columns + result | exact pair referential integrity |
| G06 | typed input + visible answer | exact acceptable answer |
| G07 | flashcard front/reveal back | exact front/back round-trip |
| G08 | image occlusion fixture | exact media hash/region/alt contract |
| G09 | canvas/image-only MCQ | OCR/vision draft, review required where uncertain |
| G10 | question without reveal | `unknown`, export blocked |
| G11 | user selection but no feedback | not treated as answer key |
| G12 | conflicting visible key and selection | source key wins; conflict recorded |
| G13 | options randomized between states | joined by stable semantic/DOM identity |
| G14 | React rerenders/animations | one question capture, no duplicates |
| G15 | same question revisited | deterministic source/card identity |
| G16 | Unicode, sub/sup, formulas | exact safe rich-text normalization |
| G17 | cross-origin iframe | screenshot fallback and explicit limitation |
| G18 | prompt injection text in page | ignored as instruction; schema-only result |
| G19 | email/token in header/URL | redacted and absent from logs/export |
| G20 | more than one correct option on single-choice control | contradiction, blocked |
| G21 | “none of the above” | preserved literally, no invented resolution |
| G22 | no correct answer in source key | quarantined, not normal MCQ |
| G23 | overlapping scroll captures | deduplicated and correctly assembled |
| G24 | missing media artifact | export blocked |
| G25 | cancellation during extraction | clean cancelled state and browser cleanup |
| G26 | Chrome toolbar capture | exact `extension-capture.v1` |
| G27 | Firefox toolbar capture | semantically identical to G26 |
| G28 | extension observe permission revoked | capture stops visibly; no further artifacts |
| G29 | `.razcapture` offline round-trip | exact artifacts/IR; no network |
| G30 | malicious archive path/symlink/hash | import rejected before extraction |
| G31 | wrong pairing origin/token | transfer rejected without persisted page data |
| G32 | screenshot with MCQ and key | reviewable exact OCR/vision draft |
| G33 | screenshot without key | answer unknown; export blocked |
| G34 | digital PDF questions + later key | correct page provenance and reviewed join |
| G35 | scanned PDF with formula | preserved crop; uncertainty requires review |
| G36 | pasted text with answer key | exact structured draft |
| G37 | pasted question without key | correct option not inferred |
| G38 | password/payment fields in selected tab | values absent from bundle |
| G39 | extension permission manifests | only approved default/optional permissions |
| G40 | approved IR → reviewed-deck | exact deterministic projection; private evidence absent |
| G41 | reviewed flashcard → razbiram-anki → `.apkg` | field/media/ID round-trip |
| G42 | reviewed single MCQ/true-false → `.apkg` | exact answer cardinality and source marker |
| G43 | multiple-select without Anki model capability | blocked; no single-answer downgrade |
| G44 | matching without Anki capability | blocked or explicit new derived deck, never implicit |
| G45 | direct handoff wrong origin/nonce/version | rejected without persistence |

Include regression fixtures based on the semantics of existing multiple-correct content, but use
synthetic wording rather than private/third-party questions.

## Exact metrics

### Capture

- Chrome/Firefox semantic parity;
- `.razcapture` hash and round-trip integrity;
- default and optional extension permission budget;
- question detection precision/recall;
- duplicate capture rate;
- missed transition rate;
- crop completeness.

### Text/structure

- normalized exact match for question and options;
- option ordering accuracy;
- card-family classification accuracy;
- rich-text token accuracy.

### Answers

- exact correct-option set accuracy;
- false-authoritative rate (target: zero);
- blocked-when-unknown rate (target: 100%);
- evidence-tier accuracy.

### Export

- schema validity;
- deterministic byte output;
- target capability enforcement;
- round-trip through product adapters;
- artifact hash/reference integrity.

## Acceptance thresholds

For DOM/ARIA fixtures:

- 100% card-family classification;
- 100% correct-option set accuracy;
- 0 false-authoritative answers;
- 0 silent incompatible exports;
- 100% deterministic identity/output.

For OCR/vision fixtures:

- thresholds are established during M3;
- no automatic approval based on confidence alone;
- answer evidence still must be source-verified or reviewer-confirmed.

## Test layers

1. pure unit tests for normalization, IDs, invariants, mapping;
2. JSON Schema and contract tests;
3. offline Playwright page fixtures;
4. Chrome/Firefox extension fixtures and manifest tests;
5. screenshot/PDF/text/bundle ingest contract tests;
6. studio E2E for review, consent, delete, export;
7. target adapter/renderer integration tests;
8. reviewed-deck/razbiram-anki cross-repo contract and round-trip tests;
9. optional real-model evaluation report pinned by provider/model/prompt version.

## Evaluation records

Each run records:

- code, schema, fixture, and prompt version;
- provider/model if any;
- per-stage durations;
- exact issues and review requirements;
- aggregate metrics;
- no raw private content.

Changing an extraction prompt, model default, semantic snapshot, or normalization rule requires a
Golden-Set comparison in the same change.
