# HANDOFF — razbiram-screen-to-learn

Session handoffs, **newest entry first**. Written at session stop and read after the Base
Constitution and BIBLE at session start.

## 2026-07-25 — Architecture, dual intake, Anki boundary, and Base onboarding

_HEAD before concept work `1f7a982` · upstream status unknown · target gate PASS · Base doctor
PASS · secure pending commit/push_

- **Done:** Completed the feasibility and solution-architecture package; specified standalone
  screenshot/PDF/text intake, Chrome/Firefox extension, Capture Lite, local pairing, Capture IR,
  review/validation/export, Razbiram CI, security, card-family capability handling, and
  razbiram-anki integration. Added the canonical `dev/base` backbone, session skills, security
  files, ownership, and CI.
- **Decided:** Conditional GO. Standalone and extension converge before extraction. Multiple
  select is lossless or blocked. Capture IR remains private; razbiram-anki connects only after
  review through a proposed hub-owned reviewed-deck contract. This repo is an MIT Bridge/Tool
  with a Razbiram identity carve-out. Base Rule of Three blocks a shared Anki code package until
  a third real consumer exists.
- **Open:** Hub approval/name for `razbiram.recall-deck.v1`; final multiple-select capability
  identifier; first cloud-vision providers; whether Safari follows Chrome/Firefox; whether a
  curated-content PR export follows file export.
- **Next:** Approve and build Roadmap M0: common screenshot/PDF/text ingest, minimal
  Chrome/Firefox fixture, `.razcapture` round-trip/pairing, reviewed-deck projection, native
  Learn JSON fixture, and one supported razbiram-anki `.apkg` round-trip.
- **Continuity warnings:** Current razbiram.com MCQ runtime is single-answer. Current
  razbiram-anki accepts `.apkg`/CrowdAnki only and cannot be treated as the universal deck
  contract. Re-check all pinned sibling commits before implementation.

### Reviewed baselines

- screenshot-to-code: `6094fd710becd981fbcf29cfc32d7ebef921866d`
- razbiram-nlp: `48b5beb`
- razbiram-anki: `119bcea`
- razbiram-listen: `6d190e2`
- razbiram.com: `fd88f7c2`
- studywithme_db: `12f9381`
