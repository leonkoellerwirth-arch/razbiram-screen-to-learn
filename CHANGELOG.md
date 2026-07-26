# Changelog

All notable changes to this project will be documented here.

The application and its data contracts use independent semantic versions.

## [Unreleased]

### Added

- CLI `extract` / `validate` / `export` and a local drop-in studio (`studio`) — the first working
  path from a captured page to a validated, capability-gated deck.
- Deterministic identifiers (`IDENTITY_ALGORITHMS.md`) shared by the Python core and the extension.
- `learncard-target.v1` schema and reference deck: the two additive card formats razbiram.com's
  engine parses — true/false (`sourceFormat`) and multiple-select (`selectionMode`).
- `CARD_TYPE_DETECTION.md` and 15 conformance vectors so any engine can auto-detect a card's shape
  from the card alone, and be tested against the same suite.
- Synthetic learning fixture covering all five card families and the randomised-option case.

### Changed

- Target capabilities are read from a pinned copy of razbiram.com's published profile instead of a
  hard-coded list, and fail closed when it is missing or malformed.
- Export now blocks a card the target cannot represent, with a human-readable reason, instead of
  degrading it.

### Added

- Feasibility assessment and conditional-GO decision.
- Content-first browser capture architecture.
- Lossless Capture IR for single-choice, multiple-select, true/false, matching, typed,
  flashcard, and image-occlusion.
- Current razbiram deck compatibility profile and multiple-select capability plan.
- Security/privacy/legal boundaries, Corporate Identity contract, Golden-Set plan, roadmap, and
  repository blueprint.
- Dual-intake concept: standalone screenshot/PDF/text studio plus downloadable Chrome/Firefox
  extension.
- Portable `.razcapture` handoff, local pairing architecture, minimum-permission model, and
  transparent Razbiram product-discovery strategy.
- Audited razbiram-anki integration design at the approved reviewed-deck boundary, including a
  proposed hub contract, capability matrix, file/direct handoff, and cross-repo Golden tests.
- `dev/base` paved-road onboarding: deterministic backbone, session lifecycle, docs-only CI,
  security configuration, CODEOWNERS, and explicit Bridge/Tool zone.
