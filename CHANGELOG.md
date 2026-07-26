# Changelog

All notable changes to this project will be documented here.

The application and its data contracts use independent semantic versions.

## [Unreleased]

### Added

- **Images as intake.** Drop a screenshot or a photo of a page and get cards. Structure is read
  from the material itself — letter markers where they exist, otherwise typography, the widget in
  front of each choice, and the colour a page uses to mark its answers. Nothing to configure, and
  no language to choose. Needs the `tesseract` binary; see the README.
- **`./start.sh`** — one command to build the studio and serve it locally.
- **Progress while you wait.** Reading a full page takes about a minute; the studio now says which
  stage it is in and how long it has been running instead of showing one unchanging label. No
  proportion is displayed that was not measured.
- **The deck JSON is editable before download**, so a card the extractor could not resolve can be
  corrected in place. Copy and download take what you see; JSON that does not parse blocks the
  download rather than handing over a file the target cannot read.
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

### Fixed

- The exporter refuses a card whose answer was never evidenced. It relied on the validator being
  called alongside it; a caller reading the deck directly would have received the card.
- A true/false question printed without an answer key is no longer demoted to single choice.
- An answer wrapped across lines no longer splits its question into fragments.
- A long deck title no longer produces a key that the deck schema rejects.

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
