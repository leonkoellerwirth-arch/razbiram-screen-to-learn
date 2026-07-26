# BIBLE — razbiram-screen-to-learn

The stable decisions and invariants for this repository. Precedence:
`../base/CONSTITUTION.md` → the family contract in
`../razbiram-nlp/docs/razbiram-ECOSYSTEM.md` → this file → agent instructions/briefings. A local
override of the Base Constitution requires a deliberate dated amendment here.

## Zone

**Bridge / Tool — MIT open source.** It never contains business-internal backend logic,
production prompts verbatim, curated private datasets, user data, or secrets. The Razbiram visual
identity remains © razbiram.com and is explicitly excluded from the MIT grant.

## Identity

razbiram-screen-to-learn is the visual learning-content entry gate of the razbiram ecosystem. It
observes user-authorized learning screens, reconstructs evidence-backed cards, and exports
reviewed razbiram-compatible JSON. It is not a crawler, answer-solving service, or publishing
backend.

## Invariants

1. **Evidence before generation.** Correctness must trace to DOM, accessibility data, a captured
   reveal/key state, or explicit human confirmation.
2. **Content-first.** Prefer structured DOM/ARIA extraction; use screenshot vision/OCR as
   corroboration or fallback.
3. **Human release gate.** Extraction may be automatic; publication/export is reviewable and
   never silently automatic.
4. **Lossless card semantics.** Single-choice, multiple-select, true/false, matching, typed,
   flashcard, and image-occlusion remain distinct in the capture IR.
5. **No false compatibility.** Multiple-select cannot be exported to a target that lacks its
   capability. Existing unsupported multiple-answer files are evidence of a runtime gap, not a
   format precedent.
6. **Stable identity.** Session, source, capture, item, option, and card identifiers are
   deterministic wherever inputs are stable.
7. **Local-first.** Captures and review data stay on the user's machine by default; no telemetry.
8. **Bounded browser automation.** No broad crawling, hidden endpoint use, paywall/DRM/CAPTCHA
   bypass, or automated access escalation.
9. **Private evidence.** Source screenshots are excluded from exported decks unless the user has
   rights and explicitly includes a derived asset.
10. **Contract ownership.** The tool owns capture and normalization. razbiram.com owns its
    render/runtime contract; shared schema changes are coordinated, additive, and versioned.
11. **Evaluator principle.** Every extraction/card-type path has Golden-Set coverage.
12. **Corporate identity.** UI follows the current razbiram token source; theme assets remain
    © razbiram.com.
13. **One core, two entry channels.** Standalone file/text import and the browser extension
    produce the same Capture IR and use the same review/export pipeline.
14. **Minimum extension privilege.** Active-tab, explicit start/stop, narrow optional site
    permissions, no cookie/history access, no debugger permission, and no all-sites capture by
    default.
15. **Branding without surveillance.** The extension may promote razbiram.com through its store
    listing, popup, onboarding, and export success state, but never through telemetry, injected
    page ads, card-content ads, or hidden referral tracking.
16. **Anki at the reviewed boundary.** Capture IR and evidence remain screen-to-learn-private.
    Approved cards may cross into razbiram-anki only through a versioned, capability-gated family
    deck contract.
17. **Base Rule of Three.** A shared Anki implementation package is not extracted for only
    razbiram-anki and screen-to-learn. The contract/handoff is shared; code remains with its owner
    until a third real consumer exists.

## Decisions

- **2026-07-25 — Adopt the dev/base paved road.** The Base Constitution, deterministic backbone,
  session lifecycle, security configs, budgets, and CI govern the repo from the concept phase.
- **2026-07-25 — Conditional GO.** Feasible with shared screenshot/PDF/text/extension intake,
  DOM-first evidence where available, human review, and capability-gated export.
- **2026-07-25 — Controlled browser first.** Superseded by the dual-intake decision below.
- **2026-07-25 — Internal IR separates capture from export.** Source quirks do not leak into the
  app-facing deck schema.
- **2026-07-25 — Existing card renderers are reused.** New product runtime work is limited to
  multiple-select; true/false reuses single-choice presentation with two options.
- **2026-07-25 — screenshot-to-code is a donor, not a fork target.** Selective MIT-attributed
  reuse replaces a wholesale rename.
- **2026-07-25 — Dual intake.** The standalone studio accepts screenshot/PDF/text/bundle imports;
  a downloadable Chrome/Firefox extension is the second capture option. Both converge on
  `capture-ir.v1`. Playwright remains useful for fixtures, controlled-browser fallback, and E2E.
- **2026-07-25 — Extension as a branded acquisition surface.** It carries the current Razbiram
  identity and honest links to razbiram.com without requiring sign-in or exporting browsing data
  for advertising.
- **2026-07-25 — razbiram-anki integration.** Adopt a reviewed-deck handoff to razbiram-anki for
  Anki/CrowdAnki outputs. Do not make CrowdAnki or current razbiram-anki app internals the Capture
  IR or universal ecosystem contract.
- **2026-07-26 — The integration boundary is the deck JSON, nothing else.** _(PARTIALLY SUPERSEDED
  the same day — see the amendment directly below.)_ razbiram.com does not
  implement, import or know about screen-to-learn; it only has to parse new card formats. Both
  additive formats are therefore specified as a schema the engine can implement against —
  `docs/schemas/learncard-target.v1.schema.json`, with a generated reference example: true/false
  as `sourceFormat: "true-false"` with exactly two options, and multiple-select as
  `selectionMode: "multiple"` with `correctOptionIds` and per-option ids. Both are tagged with an
  explicit discriminator so a parser never infers the shape from the option count. The schema
  accepts the shipped 33-card deck unchanged, so the additions break no existing content. The
  capability identifiers are settled: `mcq.true-false` and `mcq.multiple-select.v1`, as razbiram.com
  publishes them in its capability profile.
- **2026-07-26 (amendment, owner decision) — razbiram.com gets its OWN capture plugin; this repo
  is no longer the only intake.** Amends the boundary decision above. razbiram.com is building a
  standalone, client-side drop-ingest plugin (screenshot / PDF / pasted text → extracted questions
  → `studywithme-bg.learncard.v1` deck), recorded in `dev/razbiram.com/BIBLE.md` (2026-07-26).
  What still holds from the original decision: **deck JSON remains the only contract between the
  two repos.** Neither imports the other's code, and this repo is still not a dependency of
  razbiram.com. What changes: razbiram.com is now also a *producer* of that JSON, not only a
  consumer — so the two intakes must not drift.
  - This repo stays the owner of the **richer** pipeline: `capture-ir.v1`, the evidence model, the
    browser extension, and the review flow. razbiram.com's plugin is deliberately the thin,
    zero-install path.
  - The shared, non-negotiable principle both sides implement: **extraction, never generation** —
    correctness is read from the source's own answer key and never inferred (as `extract.py`
    already states). razbiram.com recorded this as a binding constraint too.
  - `docs/schemas/learncard-target.v1.schema.json` is the single shape both intakes emit. A change
    to it is a change to both.

- **2026-07-26 — Target capabilities are read from a pinned profile, and fail closed.** The
  exporter reads a committed copy of razbiram.com's `/learncards/profile.v1.json` rather than a
  hard-coded list or a live fetch: exports must work offline and a Golden run must not depend on a
  remote file. `scripts/refresh-target-profile.sh` makes updating it a reviewable act. A missing or
  malformed profile narrows to `mcq.single` — failing open would silently export families the
  engine cannot render.
- **2026-07-26 — Extraction ownership is OPEN; no new extraction code on either side.** razbiram.com
  is building its own capture plugin, so the same rules are about to exist in Python here and
  TypeScript there. See `docs/decisions/009-extraction-logic-ownership.md`.
  _(SUPERSEDED the same day — see the owner decision below.)_
- **2026-07-26 (owner decision) — Extraction lives HERE; razbiram.com consumes the deck JSON.**
  The freeze above was lifted deliberately: image intake cannot work without an extractor on this
  side. `textseg`/`textcards` began as a port of razbiram.com's `segment.ts`/`classify.ts` and now
  carry fixes the original lacks. **razbiram.com's copy is the one that should retire**; until it
  does the two are knowingly divergent and ADR 009 records how they are reunited.
- **2026-07-26 — Structure may be drawn rather than written.** Three measured signals, in
  `screenshot.py`: the two type sizes most of the page is set in are question and choice; a choice
  opens with a short, low-confidence token (the widget is not text); a row whose background departs
  from the page is marked. Indentation was measured and rejected — option starts and wrapped
  continuations overlap. Chrome is dropped as unreadable **or** wordless; neither test suffices
  alone, since a cell border reads at the confidence of a real answer.
- **2026-07-26 — Where a page marks in two colours, the MORE COMMON one means correct.** A results
  view marks every right answer but only the questions the reader got wrong. Ties bind nothing.
  Marks covering more than half a question are withdrawn: emphasis that marks everything
  distinguishes nothing. Half stays legal — true/false marks one of two.
- **2026-07-26 — The option marker sequence, not the numbering, bounds a question.** A, B, C, D
  then A again is a new question. Numbering failed first: OCR drops a leading digit readily, and
  then number-anchored segmentation merges two questions silently. Plain text after an option run
  is therefore a wrapped answer, not a new stem.
- **2026-07-26 — Family is read from the material, not from whether the answer is known.** A
  true/false question printed without its key is still true/false; the ported rule demoted it to
  single-choice, losing the distinction invariant 4 exists to keep.
- **2026-07-26 — No user-facing language choice.** This tool turns material into cards; it is not a
  language product. Every preferred tesseract model present is loaded at once.
- **2026-07-26 — A local LLM is a fallback, never the structurer.** Measured on real OCR text:
  `aya-expanse:8b` dropped the last option of every question; `llama3.2` split wrapped options into
  separate answers. Both fail silently, which for exam material means teaching an incomplete
  question. The seam stays open at `model-inferred`, which `EXPORTABLE_TIERS` already refuses
  without human confirmation — but geometry leads.
- **2026-07-26 — Progress reports only what was measured.** Upload bytes, OCR attempt n of a known
  ladder, card n of m. Absent a proportion the bar paces; `total` is an upper bound, so stopping
  early reads as success.
- **2026-07-26 — The razbiram-anki round-trip is out of M0 scope.** It gates M2A instead. M0 could
  not otherwise exit without first delivering M2A: the round-trip needs the hub-owned
  `razbiram.recall-deck.v1` contract and a razbiram-anki import path, neither of which exists. M0
  stays a local vertical slice; the integration itself is unchanged.
- **2026-07-27 — The studio always shows the recognised deck; a gate, not a hidden panel, decides
  what may leave.** The export panel rendered the JSON editor only when an export existed, so a run
  reading "0 exportable · 3 blocked" showed nothing to look at — the recognised cards existed and
  were unreachable. The editor now opens on the export, or on a **draft** (`draft.py`) holding every
  recognised card in target shape with the unevidenced parts empty. Download is gated on
  `POST /v1/deck/check`, which runs the export path's own rules against the edited JSON. This closes
  the previous session's "no review step in the studio" gap, in the shape the owner chose for
  razbiram.com as well: JSON-only authoring, no card builder.
- **2026-07-27 — A draft never carries an answer the export would not accept.** A card blocked for
  its evidence tier still holds the extractor's reading of an ambiguous source. Copying that into
  the draft made the deck structurally complete, so the gate cleared it and Download turned green on
  an answer nobody evidenced — found in the studio on a real quiz, not by a test. An unqualified
  `answerEvidenceTier` now drafts as unanswered. _Why it is in the register:_ structure is not
  evidence, and a pre-filled guess a person confirms is indistinguishable from a fabricated answer
  (invariant 1, reached through invariant 3).

## Open product decisions

- Loopback pairing is the first interactive transport; Capture Lite is the no-app fallback.
  Native Messaging remains an optional packaged-companion decision after M2E.
- Which cloud vision providers are enabled in the first public release; provider interfaces are
  mandatory either way.
- Whether the first product release exports only files or also prepares a curated-content pull
  request. Direct platform upload is out of MVP scope.
- The final family-owned identifier for the additive multiple-select capability.
- Hub approval and final identifier for the proposed `razbiram.recall-deck.v1` family contract.
- Whether Safari Web Extension packaging joins the first extension release or follows after the
  Chrome/Firefox protocol is proven.
