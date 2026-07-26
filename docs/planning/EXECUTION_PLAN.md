# Execution plan — architecture repair, then M0

Consecutive, resumable plan produced by the 2026-07-26 pre-implementation architecture review.
Work top to bottom. Every item is independently completable and revertible.

**Resume protocol.** Any session can continue here: run `./scripts/state.sh`, read the newest
`HANDOFF.md` entry, then take the first unchecked item in the lowest unfinished phase. Tick the box
in the same commit that does the work. A phase is done when every box in it is ticked and
`./scripts/gate.sh` is green.

Legend: `[ ]` open · `[x]` done · `[!]` blocked, needs a decision or another repo.

> Phases 1–4 are documentation and schema work only. No implementation begins before Phase 5.
> This is deliberate: the review found that M0's core deliverable rests on a contract that is not
> yet specified end-to-end.

---

## Review inputs

Three independent reviews, all findings below re-verified by hand against the files:

- extension architecture (`BROWSER_EXTENSION.md`, `BROWSER_CAPTURE.md`, extension schema, ADR 004/007);
- core solution architecture (`SOLUTION_ARCHITECTURE.md`, `PIPELINE.md`, `DATA_CONTRACTS.md`,
  `REPOSITORY_BLUEPRINT.md`, schemas, `FEASIBILITY.md`, `GOLDEN_SET.md`, ADR 001/002/003/005);
- ecosystem-claim verification against the live `razbiram.com`, `razbiram-anki`, `razbiram-nlp`,
  `razbiram-listen` and `studywithme_db` checkouts.

---

## Phase 0 — Backbone and session hygiene

- [x] **P0.1 — Commit the Claude hook wiring.** `.claude/hooks/*.sh` were tracked but dormant: no
      `.claude/settings.json` existed, so neither the sensitive-file guard nor the lint-on-edit
      guard ever ran. `.claude/settings.json` now wires `PreToolUse`, `PostToolUse`, and a `Stop`
      budget warning. Smoke-tested: prod-env write blocked (exit 2), normal write allowed (exit 0).
      *Done when:* committed, and the same gap is reported to `razbiram-listen` / `razbiram-nlp`,
      which have identical dormant hooks.
- [x] **P0.2 — Re-pin `studywithme_db`.** `HANDOFF.md:38` pins `12f9381`; the repo is one commit
      ahead at `553e857` ("Add: Anki processing workflow"). Verified that commit does **not** touch
      `app/studywithme-bg/learncards/`, so the reference deck is unaffected.
      *Done when:* the pin reads `553e857`, or the entry states the pin is deliberately one behind.
- [x] **P0.3 — Confirm the other five pins.** `screenshot-to-code 6094fd7`, `razbiram-nlp 48b5beb`,
      `razbiram-anki 119bcea`, `razbiram-listen 6d190e2`, `razbiram.com fd88f7c2` all exist and are
      each repo's current HEAD. *Done when:* recorded in `HANDOFF.md` as re-verified 2026-07-26.

---

## Phase 1 — Repair the evidence-join contract (BLOCKING)

The single most important finding. Four documents describe the question↔reveal join, and no two of
them agree. This sits directly under M0's core deliverable, so it must be settled first.

- [x] **P1.1 — Fix the fingerprint/join contradiction.**
      `BROWSER_CAPTURE.md:140` hashes "normalized option texts **in source order**" into
      `questionFingerprint`. `PIPELINE.md:71` joins question and reveal states by grouping on
      `questionFingerprint`. `GOLDEN_SET.md:35` requires case G13 — *options randomized between
      states* — to join successfully. If option order changes between the two states, the
      fingerprint changes and the join silently fails, so G13 cannot pass as specified.
      *Decide:* either sort option texts before hashing, or make the join key something other than
      `questionFingerprint` (G13's own expectation says "stable semantic/DOM identity").
      *Done when:* one mechanism is stated in `BROWSER_CAPTURE.md` and `PIPELINE.md` agrees with it.
- [x] **P1.2 — Add `captureState` to `extension-capture.v1`.** Verified: the schema's top-level
      properties are `schemaVersion, captureId, createdAt, extension, page, captureMode, artifacts,
      privacy, questionFingerprint` — there is no way to say whether a capture *is* the question
      state or the reveal state. `BROWSER_CAPTURE.md:155-169` defines `QuestionCaptured` and
      `RevealCaptured` as distinct states of one question; the Join stage must currently open and
      parse artifacts to find out which it holds. `additionalProperties: false` means this cannot be
      added later without a version bump.
      *Done when:* `captureState` (enum) and `stateFingerprint` exist in the schema and the example.
- [x] **P1.3 — Make `questionFingerprint` required, or state why it is optional.** It is absent
      from the schema's `required` array while `PIPELINE.md:71` treats it as the join key.
- [x] **P1.4 — Publish `semantic-snapshot.v1.schema.json`.** Verified absent from `docs/schemas/`.
      `semantic/question.json` is the artifact the Detect, Extract, and Join stages actually read,
      and it is the only major artifact with no published schema — while `DATA_CONTRACTS.md:7-14`
      lists `extension-capture.v1` as a *public* contract. Without it, the TypeScript extension and
      the Python extractors can diverge silently, and M0's IR validator cannot validate extension
      input. Minimum fields: node type, role, accessible name, visible text, normalized bounding
      box, checked/expanded/disabled flags, shadow-root indicator, container reference.
- [x] **P1.5 — Give `captureMode: "region"` a home for its geometry.** The enum accepts `"region"`
      but no field carries the CSS-pixel rect and device-pixel ratio that
      `BROWSER_EXTENSION.md:43-47` says are stored. Simplest fix: define it in the P1.4 snapshot
      schema and cross-reference it.
- [x] **P1.6 — Specify the identity algorithms.** `DATA_CONTRACTS.md:333` defines `sourceId` as
      "SHA-256 of source scope + question fingerprint" — neither input is fully defined, and
      "normalized" is never defined (Unicode form? whitespace? case? markup stripping?). Serialize
      exactly, or two implementations will disagree and `GOLDEN_SET.md:111`'s "100% deterministic
      identity" threshold cannot hold. Also resolve `DATA_CONTRACTS.md:334`, where `cardId` is given
      two incompatible definitions joined by "or".
      *Suggested home:* `docs/architecture/IDENTITY_ALGORITHMS.md`.

---

## Phase 2 — Align the export contract with the live product (BLOCKING)

The documented compatibility target diverges from the deck the product actually ships. An exporter
built to the current text would emit files the runtime cannot read.

- [x] **P2.1 — `access` vs `accessTier`.** `DATA_CONTRACTS.md:309` instructs "Use `accessTier`, not
      the legacy/drifted `access` key." Verified against the live file
      `studywithme_db/app/studywithme-bg/learncards/Biophysics/config.json`: its keys are
      `topicKey, access, year, semester, title, description, typedAnswerEvaluation, decks` —
      it uses **`access`**, and `accessTier` does not appear. The documented rule is an aspiration,
      not the contract. *Action:* audit the razbiram.com config loader; until it accepts
      `accessTier`, the exporter writes `access` (or both). Also note `typedAnswerEvaluation`, which
      the documented shape omits entirely.
- [x] **P2.2 — Correct the `meta.source` hull.** `DATA_CONTRACTS.md:229-233` documents
      `{"kind": "browser-capture", "rightsBasis": "permission-confirmed"}`. The real reference deck
      has `{"file": "deck.json", "book": "Biophysics Exam Preparation", "originalDeckName":
      "L1 Cybernatics"}` — Anki-import provenance. Mark the documented shape as the *proposed output
      shape for new exports* and require the validator to accept both.
- [x] **P2.3 — Name the repo that owns the reference deck.** `DATA_CONTRACTS.md:211-212` cites
      `app/studywithme-bg/learncards/Biophysics/deck-01.json` without saying it lives in
      **`studywithme_db`**, not `razbiram.com`.
- [x] **P2.4 — Record what was confirmed correct.** `schemaId: studywithme-bg.learncard.v1`, the
      single-choice output shape, `correctAnswer` as a singular string, `scoring.mode:
      single-best-answer`, and `cardCount: 33` matching 33 real cards all verified accurate.
      razbiram.com's MCQ runtime is confirmed single-answer at every layer: `role="radiogroup"`,
      `correctAnswer?: string`, and a validator that rejects more than one correct option. The
      multiple-select continuity warning is accurate and stands.

---

## Phase 3 — Internal consistency (SHOULD-FIX)

- [x] **P3.1 — One canonical schema path.** `REPOSITORY_BLUEPRINT.md:41-48` puts schemas at
      root-level `schemas/` as `capture-ir.v1.json`; the real files are `docs/schemas/` as
      `capture-ir.v1.schema.json`, which is what `DATA_CONTRACTS.md:117` cross-references. The
      `QUALITY_AND_CI.md:26` "generated schemas match committed schemas" gate needs one true path.
      Also mark `reviewed-deck.ref.json`, `event-protocol.v1.json`, `validation-report.v1.json` as
      later deliverables — they are in the tree but do not exist.
- [x] **P3.2 — Close the schema typo loophole.** `capture-ir.v1.schema.json` uses
      `"additionalProperties": true` at lines 236 (`option`), 599 (`card`), 779 (`evidence`) while
      using `false` for every other object. A typo like `corectOptionIds` validates clean today.
      Prefer `"unevaluatedProperties": false`, which composes correctly with the `allOf`/`if`/`then`
      family discrimination.
- [x] **P3.3 — Name the cross-field validators explicitly.** JSON Schema cannot express
      `correctOptionIds` == the set of `isCorrect: true` ids (`DATA_CONTRACTS.md:174`),
      `meta.cardCount === cards.length`, or evidence referential integrity. List them in
      `QUALITY_AND_CI.md` as code-validator duties so nobody assumes the schema covers them.
- [x] **P3.4 — Repair `capture-ir.v1.example.json`.** Verified: its top-level keys are
      `schemaVersion, sessionId, source, target, deck, cards` — there is **no** `evidence` array,
      yet its cards reference `ev_question_dom`, `ev_key_a`, `ev_key_b`, `ev_key_c`. The primary
      contract fixture ships dangling references and still passes schema validation.
- [x] **P3.5 — Fill the logical-component gaps.** `SOLUTION_ARCHITECTURE.md:75-142` defines seven
      modules; `REPOSITORY_BLUEPRINT.md:29-39` has thirteen. `api`, `jobs`, `pairing`, `security`,
      and `storage` exist only in the tree — and `pairing` carries real security requirements.
      `AGENTS.md:5` sends agents to `SOLUTION_ARCHITECTURE.md` as the primary reference, so the gap
      matters.
- [x] **P3.6 — Specify loopback port discovery.** Both reviews raised this independently.
      `SOLUTION_ARCHITECTURE.md:205` says "ephemeral port"; `BROWSER_EXTENSION.md:169` says "random
      port"; `BROWSER_EXTENSION.md:162-165` describes a pairing code — but nothing says how the
      extension learns the port. Range-scanning is a security anti-pattern and is ruled out by the
      strict Host/Origin checks. ADR 007:43 makes the pairing protocol a public compatibility
      boundary, so it must be pinned down before M2E. Token authentication is sound either way;
      port secrecy is not a claimed property.
- [x] **P3.7 — Fix the reuse-table framing.** `REPOSITORY_BLUEPRINT.md:133` bills
      `backend/asset_extraction.py` as "EXIF/pixel/crop/schema-output helpers"; at the pinned commit
      it is a Gemini-specific extraction pipeline whose generic parts must be carved out.
      `UPSTREAM_REUSE.md:162-179` already describes this accurately — align the blueprint to it.
      All eight upstream files were confirmed to exist at `6094fd7`; no phantom reuse claims.

---

## Phase 4 — Decisions and cross-repo unblocking

- [x] **P4.1 — DECIDED 2026-07-26: the razbiram-anki round-trip is out of M0 scope.** `ROADMAP.md:22`
      made M0 exit on all twelve `FEASIBILITY.md` criteria, but criteria 10–11 required a
      reviewed-deck handoff to razbiram-anki and a real `.apkg` round-trip — needing the
      `razbiram.recall-deck.v1` schema (does not exist), a razbiram-anki import path (does not
      exist), and cross-repo golden tests, all scheduled in **M2A**. M0 therefore could not exit
      without doing M2A. *Resolution:* the two criteria moved out of the M0 proof-of-concept list
      into a new "M2A gate criteria" section of `FEASIBILITY.md`; the remaining M0 criteria
      renumbered 1–10; `ROADMAP.md` M0 exit now states the round-trip is out of M0 scope, and M2A
      carries its own exit line. The razbiram-anki integration itself is unchanged — ADR 008, BIBLE
      invariant 16, and the M2A milestone all stand. M0 is now a purely local vertical slice.
- [!] **P4.2 — File razbiram-nlp ADR 006 for `razbiram.recall-deck.v1`.** Confirmed the contract
      does not exist anywhere in the family. The hub has no `schemas/` directory at all; its
      contract source of truth is Pydantic 2 models in `src/razbiram_nlp/models.py` with
      `extra="forbid"`, and ADRs live at `docs/adr/NNN-title.md` (001–003 still unwritten). Follow
      that convention rather than inventing one. Blocks P4.3 and all M2A work.
- [x] **P4.3 — Do not build `packages/generated-contracts/` yet.** `REPOSITORY_BLUEPRINT.md:24`
      plans generated TypeScript types for a hub contract that does not exist. razbiram-listen
      already hit this: its BIBLE decision D7 records a hand-kept `contract.py` mirror that exists
      "only until the hub publishes a JSON Schema." Building the TypeScript equivalent against a
      *non-existent* contract repeats a lesson the family already paid for. Defer until P4.2 lands.
- [x] **P4.4 — Align the blueprint with the family pattern.** `REPOSITORY_BLUEPRINT.md:57-60` lists
      only `gate.sh` and budget scripts; the established sibling backbone is five scripts —
      `state.sh`, `gate.sh`, `secure.sh`, `session-snapshot.sh`, `budget.sh` — and `state.sh` and
      `session-snapshot.sh` are load-bearing for the session skills. This repo *has* all five; only
      the blueprint text is wrong.
- [x] **P4.5 — Record the CEFR colour trap.** Both `razbiram-listen` and `razbiram-anki` recorded
      that the ECOSYSTEM.md CEFR colour table conflicts with the real CSS tokens in
      `razbiram-nlp/web/styles.css`, with an explicit "don't 'correct' them" warning. The Studio UI
      must take token values from the CSS, not the table. Add to `CORPORATE_IDENTITY.md`.
- [ ] **P4.6 — Decide the `downloads` permission.** `BROWSER_EXTENSION.md:93-95` defers it. In
      observe mode the popup is usually closed when a bundle is ready, and an MV3 service worker
      cannot call `URL.createObjectURL()` — so Capture Lite would need `chrome.downloads`. Either
      declare it now with a store justification, or document that observe-mode Capture Lite requires
      the user to open the popup per bundle. Deciding after store submission costs a re-review.

- [x] **P4.7 — RESOLVED 2026-07-26: true/false is supported, the platform change is in flight.**
      The live validator required 3-5 mcq options with no `sourceFormat` handling and no
      true/false exception (`deckSchema.ts:200`), so the documented two-option export was
      rejected. That change is being made in razbiram.com, so this repo now declares
      `mcq.two-option.v1` and exports true/false as a two-option MCQ carrying
      `sourceFormat: "true-false"`. `FEASIBILITY.md` criterion 6 stands unchanged.
      *Open reconciliation, not blocking:* the capability identifier used here is provisional —
      confirm it against what razbiram.com actually ships, together with the option-count
      exception. Until then the export is correct by construction but unverified end to end
      against the live product. See P4.8.
- [x] **P4.8 — Specify the two additive deck formats for the engine.** razbiram.com does not
      integrate screen-to-learn; it only parses deck JSON. Both formats are now specified in
      `docs/schemas/learncard-target.v1.schema.json` with a generated reference example covering
      all three mcq shapes plus flashcard. Verified in both directions: the schema accepts the
      committed examples, our real export, and the shipped 33-card deck.
- [x] **P4.9 — DONE: identifiers settled and now read, not hard-coded.** razbiram.com publishes
      `/learncards/profile.v1.json`; the names are `mcq.true-false` and `mcq.multiple-select.v1`.
      `mcq.two-option.v1` was invented here and is gone. The exporter reads a pinned copy of that
      profile and fails closed if it is missing or malformed.
- [x] **P4.10 — DONE: razbiram.com renders both formats.** Implemented there on branch
      `feat/learncard-multiselect-truefalse`, Phases 1-3 of its own design doc: schema contract,
      renderer + dispatch + a11y contract, capability profile. Verified end to end — a deck
      exported from this repo resolves every card to the mode it was authored as.
- [x] **P5.12 — Studio UI adopted from razbiram-anki.** React 19 + Vite under `apps/studio`, the
      donor's `styles.css`, class names, NodeMark and theme handling kept; only the middle
      replaced (POST to the loopback API instead of in-browser Anki conversion). Tailwind 4 via
      `@tailwindcss/postcss` as the donor does. `gate.sh` now detects `apps/studio` — it
      previously skipped everything under `apps/` in silence.
- [ ] **P5.11 — Vendor the razbiram typefaces locally.** The adopted `razbiram-anki` shell loads
      Manrope/Unbounded/PT Serif from Google Fonts. The studio drops that link: it is local-first
      and must not send the user's IP to a third party on launch, nor break offline Golden runs.
      Self-host the faces under `apps/studio/public/fonts/` so the identity is exact again.

---

## Phase 5 — M0 implementation (only after Phases 1–4)

Ordered so each slice is demonstrable and revertible. Detail is deliberately thin here; refine each
slice when its phase starts, against the then-repaired contracts.

- [x] **P5.1** Repo skeleton: `pyproject.toml`, `src/razbiram_screen_to_learn/`, `tests/`, ruff +
      pytest. Gate must stay green from the first commit — it activates the Python checks
      automatically.
- [x] **P5.2a** `capture-ir.v1` Pydantic models and all eight P3.3 cross-field validators, with
      the export capability gate. Round-trip test asserts the models and the committed schema agree.
- [ ] **P5.2b** Pydantic models for `ingest-envelope.v1`, `extension-capture.v1` and
      `semantic-snapshot.v1`.
- [ ] **P5.2c** Decide the schema-generation direction. `REPOSITORY_BLUEPRINT.md` says Pydantic
      generates the schemas and `QUALITY_AND_CI.md:26` gates on "generated schemas match committed
      schemas" — but the committed schemas are hand-written, and a generated schema never
      reproduces a hand-written one byte for byte ($defs naming, keyword order, `unevaluatedProperties`
      composition). P5.2a treats the committed schema as the wire contract and the models as a
      typed view, asserting *agreement* on the shared example instead. Either ratify that and
      reword the CI gate, or commit to generating the schemas and regenerate them all.
- [ ] **P5.3** `ingest/`: screenshot, text, and PDF adapters into one envelope; the three fixtures
      from `FEASIBILITY.md` criterion 3. *Partial:* the studio and CLI accept HTML/text today and
      share one pipeline, but there is no `ingest-envelope.v1` layer, no image adapter and no PDF
      adapter. Criterion 3 ("screenshot, text, digital PDF and scanned-PDF fixtures enter the same
      IR") is therefore NOT met yet.
- [x] **P5.4** Identity module implementing P1.6 exactly, with determinism tests that hash the same
      input twice through independent paths.
- [x] **P5.5** Synthetic learning-page fixture with question/reveal transitions (owned content, no
      third-party capture).
- [ ] **P5.6** Minimal WebExtension fixture on `activeTab`, emitting `extension-capture.v1` with the
      P1.2 `captureState`. Include an observe-mode wake-on-message smoke test — MV3 service-worker
      termination mid-capture is the riskiest unproven assumption in the package and is currently
      not exercised until M2E.
- [ ] **P5.7** `.razcapture` offline round-trip; paired loopback per the P3.6 decision, rejecting
      bad origin, token, hash, and size.
- [ ] **P5.8** Extract + join for single-choice and true/false, proving the P1.1 join under
      randomized option order (G13).
- [ ] **P5.9** Capability-gated exporter to the P2-corrected target shape; multiple-select extracted
      losslessly and **blocked**, never downgraded.
- [ ] **P5.10** Golden cases for single-choice, true/false, multiple-select, flashcard, and
      image-occlusion; offline, deterministic, wired into `gate.sh`.

---

## Deferred — recorded, not scheduled

- Chrome Web Store manual review is certain given `scripting` + `captureVisibleTab` + host
  permissions. Draft the privacy justification text as an M2E deliverable, not at submission.
  The minimum-privilege posture (no `<all_urls>`, cookies, history, or debugger) is the strongest
  available single-purpose argument.
- Declare minimum browser versions (Firefox 115 is a defensible floor for MV3 +
  `captureVisibleTab` parity) before M2E acceptance testing.
- `razbiram-anki`'s frozen `legacy/` Python CLI already converts an `EnrichedDocument` to `.apkg`.
  It is explicitly "not a pattern to extend", but it is a useful reference for M2A.

---

## Confirmed sound — do not relitigate

The review found these correct as specified: the correctness-tier gating (only `source-verified`
and `reviewer-confirmed` reach export); the failure taxonomy; the data-plane/control-plane split
that keeps binary artifacts off the WebSocket; `maxItems: 1` correctly enforcing single-choice;
the retention model defaulting to deletion; the `activeTab` permission model and just-in-time
escalation for observe mode; transport security resting on capability tokens rather than CORS
alone; the honest treatment of `captureVisibleTab`'s viewport limit; the machine-checkable
`privacy` exclusion object; deferring Native Messaging; and the dual-intake decision in ADR 007.
