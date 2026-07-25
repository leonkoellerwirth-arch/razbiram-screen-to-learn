# razbiram-anki bridge

## Verdict

Connecting the products makes sense, but the integration boundary must be the **reviewed deck**,
not Capture IR and not the current `razbiram-anki` application internals.

Recommended ecosystem flow:

```text
screen/PDF/text/tab
→ screen-to-learn evidence + review
→ proposed razbiram.recall-deck.v1
├→ native razbiram Learn JSON
└→ razbiram-anki → CrowdAnki deck.json / styled .apkg
```

This gives students an immediate choice after review:

- `Download native Razbiram Learn JSON`;
- `Open in razbiram-anki`;
- `Download for Anki (.apkg)`, when the Anki capability profile supports every card.

## Audited baseline

Reviewed `razbiram-anki` commit: `119bcea`.

The current code proves:

- `razbiram-anki` accepts `.apkg` or an existing CrowdAnki `deck.json`;
- its output model is CrowdAnki `Deck → NoteModel/Note/children`, not
  `studywithme-bg.learncard.v1`;
- it can write a real `.apkg` and preserve media, note GUIDs, models, and hierarchy;
- it is currently a private Vite application package with no reusable package export;
- razbiram.com's CrowdAnki adapter converts only MCQ, flashcard, and image-occlusion note
  patterns;
- its all-in-one MCQ adapter rejects a note unless exactly one option is correct;
- matching and typed LearnCard semantics are not available through that CrowdAnki adapter.

Therefore `Capture IR → current razbiram-anki deck.json → razbiram.com` would be a lossy detour.
It would also confuse two files both called `deck.json` that have unrelated structures.

## Correct ownership

### screen-to-learn owns

- source intake and browser evidence;
- answer-evidence tiers;
- review and approval;
- private Capture IR;
- projection from reviewed Capture IR into the shared reviewed-deck contract;
- native razbiram Learn JSON export and its capability check.

### razbiram-anki owns

- mapping reviewed cards to explicit Anki note models;
- CrowdAnki `deck.json`;
- `.apkg` writing and Anki import fidelity;
- Anki media packaging;
- optional Razbiram styling inside Anki;
- Anki-specific capability and degradation reports.

### razbiram-nlp hub owns

- the proposed `razbiram.recall-deck.v1` JSON Schema and generated contract types;
- contract versioning and migration policy;
- a Mini-ADR introducing a second family contract beside `EnrichedDocument`.

`EnrichedDocument` remains the linguistic reading-document contract. A reviewed card deck should
not be forced into token/sentence/vocabulary fields merely to appear ecosystem-compatible.

## Shared reviewed-deck contract

`razbiram.recall-deck.v1` is a proposal, not an existing implementation. It should contain only
approved, portable learning semantics:

- stable deck/card/option/media IDs;
- localized title, prompt, answers, hints, and explanations;
- explicit card family;
- single vs multiple answer cardinality;
- true/false source format;
- matching pairs;
- typed acceptable answers;
- flashcard front/back;
- image-occlusion image and region references;
- provenance summary such as `source-verified` or `reviewer-confirmed`;
- rights/publication status;
- media manifest with hashes.

It must not contain:

- screenshots or DOM snapshots by default;
- browser origins with personal paths/query parameters;
- cookies, credentials, model prompts, or provider keys;
- the complete review audit trail;
- target-specific Anki templates or razbiram.com UI fields.

Capture IR stays richer and private. The reviewed-deck projection is one-way and blocks any card
with unresolved evidence, rights, or schema issues.

## Capability matrix

Current code is not equivalent to future bridge support. The bridge must negotiate capabilities
per target:

| Card family | Native Razbiram JSON | Anki bridge direction |
|---|---|---|
| Single-choice | supported | canonical Question/Option/Correct note model |
| True/false | two-option MCQ | same canonical MCQ model with source marker |
| Flashcard | supported | canonical Front/Back model |
| Image occlusion | supported | new tested native/family Anki model required |
| Typed | supported | new `type:Answer` Anki model required |
| Multiple-select | platform patch required | custom Anki model possible; must preserve the full set |
| Matching | supported | block v1; optional user-requested pair-card derivation is a new deck, not round-trip |

The exporter must not claim that the existing CrowdAnki-to-razbiram adapter can round-trip all
these types. In particular, current multiple-answer MCQs are rejected or misrepresented.

## Integration phases

### Phase A — portable handoff

Add `razbiram.recall-deck.v1.json` download to screen-to-learn and matching file input to
razbiram-anki. This is deterministic, offline, browser-neutral, and easy to test.

### Phase B — direct browser handoff

`Open in razbiram-anki` opens the known application origin and performs a user-initiated,
nonce-bound `postMessage`/`MessageChannel` handshake:

1. exact target origin, never `*`;
2. protocol/version and capability exchange;
3. user confirms deck title/card count in the receiving app;
4. the reviewed deck and media transfer as structured data/`ArrayBuffer`;
5. receiver validates schema, sizes, hashes, and capabilities before persistence;
6. file download/upload remains the fallback.

The handoff is local browser-to-browser communication. It does not require an account, backend
upload, URL-embedded deck, or analytics.

### Phase C — reusable Anki core only after Rule of Three

Do not extract a shared package for only razbiram-anki and screen-to-learn. Under
`dev/base/CONSTITUTION.md` §8, the implementation stays in razbiram-anki until a **third real
consumer** needs in-process `.apkg` generation. Only then consider a versioned package such as
`@razbiram/anki-core`:

- reviewed-deck → canonical Anki models;
- CrowdAnki builder;
- `.apkg` writer;
- media packager;
- capability report.

Until then, use the reviewed-deck file/direct-handoff contract. Do not import files from another
repo by relative path. If the Rule of Three is eventually met, the package requires public
exports, SemVer, contract tests, and retained MIT/brand notices.

## Required cross-repo work

### In razbiram-nlp

- Mini-ADR for the reviewed-deck family contract;
- JSON Schema plus generated Python/TypeScript types;
- migration and compatibility policy.

### In razbiram-anki

- accept `razbiram.recall-deck.v1`;
- add canonical note-model builders;
- show a per-card capability report;
- preserve stable IDs and media hashes;
- test `.recall-deck → .apkg → parse` by card family;
- add exact-origin direct-handoff receiver only after file handoff is green.

### In screen-to-learn

- project approved Capture IR to the shared contract;
- add native Learn JSON and Anki handoff as sibling exporters;
- retain all evidence privately;
- block unsupported Anki families without silent flattening;
- add cross-repo Golden fixtures pinned to contract versions.

## Decision

Adopt the integration as an ecosystem goal. Do not make `razbiram-anki` a dependency of capture,
OCR, review, or validation, and do not use CrowdAnki `deck.json` as the universal family
contract.
