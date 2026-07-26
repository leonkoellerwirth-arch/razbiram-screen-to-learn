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
- **2026-07-26 — The integration boundary is the deck JSON, nothing else.** razbiram.com does not
  implement, import or know about screen-to-learn; it only has to parse new card formats. Both
  additive formats are therefore specified as a schema the engine can implement against —
  `docs/schemas/learncard-target.v1.schema.json`, with a generated reference example: true/false
  as `sourceFormat: "true-false"` with exactly two options, and multiple-select as
  `selectionMode: "multiple"` with `correctOptionIds` and per-option ids. Both are tagged with an
  explicit discriminator so a parser never infers the shape from the option count. The schema
  accepts the shipped 33-card deck unchanged, so the additions break no existing content. The
  capability identifiers remain provisional pending the family-owned names.
- **2026-07-26 — The razbiram-anki round-trip is out of M0 scope.** It gates M2A instead. M0 could
  not otherwise exit without first delivering M2A: the round-trip needs the hub-owned
  `razbiram.recall-deck.v1` contract and a razbiram-anki import path, neither of which exists. M0
  stays a local vertical slice; the integration itself is unchanged.

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
