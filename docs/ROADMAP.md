# Implementation roadmap

Roadmap items are planned, not promised. Each milestone ends in an independently demonstrable,
revertible result.

## M0 — Architecture spike

Deliver:

- screenshot, text, and selected-page PDF ingest fixtures;
- minimal Chrome/Firefox WebExtension fixture using active-tab permission;
- `.razcapture` schema, offline round-trip, and paired loopback protocol spike;
- headed Playwright session with a dedicated temporary profile as fallback;
- synthetic learning-page fixture with question/reveal transitions;
- DOM, accessibility-derived semantic snapshot, and cropped PNG artifact;
- deterministic question fingerprint;
- `capture-ir.v1` writer/validator;
- single-choice, true/false, multiple-select, flashcard, and image-occlusion Golden cases;
- capability-gated exporter.

Exit: all proof-of-concept criteria in `evaluation/FEASIBILITY.md` pass.

## M1 — Core local pipeline

Deliver:

- typed stage interfaces;
- local job queue, progress, cancellation, retry, and idempotency;
- session/capture artifact store and retention policy;
- generic question-container detector;
- DOM-first extractors for radio, checkbox, true/false, flashcard, and matching;
- deterministic validation and deduplication;
- CLI commands `studio`, `capture`, `extract`, `validate`, and `export`.
- adapter-independent ingest envelope and screenshot/PDF/text/bundle adapters.

## M2 — Standalone review studio

Deliver:

- Razbiram Momentum shell;
- side-by-side evidence and extracted card;
- keyboard-complete editing and confirmation;
- uncertainty/provenance panel;
- card-type-specific editors;
- deck metadata/config editor;
- JSON preview and validation report;
- delete/export flows;
- English and German UI strings.

## M2E — Chrome and Firefox extension

Deliver:

- shared WebExtension core with Chromium Manifest V3 and Firefox packaging;
- toolbar capture, region selection, and explicit origin-scoped observe mode;
- visible capture indicator and start/pause/stop controls;
- Capture Lite `.razcapture` download;
- paired loopback transfer with origin, token, hash, and size validation;
- permission-budget tests, store privacy disclosures, and reproducible bundles;
- Razbiram Momentum popup, onboarding, icon set, and store assets;
- optional post-export razbiram.com discovery link without forced account or content telemetry.

M2E may progress in parallel with M2 after the M0 protocol spike, but it cannot fork extraction,
review, or export logic.

## M2A — Ecosystem reviewed-deck and razbiram-anki handoff

Cross-repo deliverables:

- `razbiram-nlp` Mini-ADR for a reviewed-card/deck family contract;
- proposed `razbiram.recall-deck.v1` schema and generated Python/TypeScript types;
- deterministic approved Capture IR → reviewed-deck projection;
- reviewed-deck file import in razbiram-anki;
- canonical Anki models for the supported capability subset;
- `.reviewed-deck → .apkg → parse` Golden round-trips;
- per-card capability report with no silent degradation;
- `Open in razbiram-anki` exact-origin handshake after file handoff is green.

M2A does not block the first native Razbiram JSON vertical slice, but it is part of the ecosystem
release rather than an unrelated future integration.

## M3 — Vision/OCR fallback

Deliver:

- local OCR adapter;
- optional cloud vision providers with per-job consent;
- schema-constrained extraction;
- crop/region tooling;
- formula and rich-text normalization;
- maximum one schema-repair pass;
- model/cost/run metadata without sensitive page content in logs.

## M4 — Multiple-select platform capability

Coordinated razbiram.com work:

- additive card contract and capability identifier;
- `Set<optionId>` state;
- checkbox semantics and explicit Submit;
- all-or-nothing scoring and reviewed partial-credit policy;
- feedback for selected/correct/missed options;
- memory/review metadata;
- validator, adapter, renderer, accessibility, and E2E tests;
- migration/regression tests for existing multiple-correct corpus cards.

Screen-to-learn work:

- capability negotiation;
- lossless multiple-select exporter;
- target-version compatibility report.

## M5 — Hardening and packaging

Deliver:

- one-command local start;
- packaged controlled-browser fallback;
- signed Chrome Web Store and Firefox Add-ons artifacts;
- pinned screen-to-learn/reviewed-deck/razbiram-anki compatibility matrix;
- loopback origin/host/capability-token security;
- resource and cost limits;
- secret scanning, dependency audits, SBOM;
- complete offline CI and Golden-Set;
- signed release artifacts and update documentation.

## M6 — Optional Safari/native capture

Evaluate after Chrome/Firefox usage and permission data are understood:

- Safari Web Extension packaging;
- signed macOS companion with Native Messaging if loopback pairing is insufficient;
- user-mediated ScreenCaptureKit region/window capture as a visual-only fallback;
- iOS/Safari constraints and explicit system capture consent.

No native option may claim global silent capture or weaken the shared evidence contract.
