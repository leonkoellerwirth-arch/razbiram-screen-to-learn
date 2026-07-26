# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Status

Documentation-first. No runtime code exists yet: no `pyproject.toml`, `package.json`, `src/`, or
tests. The `docs/` architecture package is a plan, not a description of shipped code. Do not start
broad implementation before the M0 acceptance criteria in `docs/ROADMAP.md` are approved.

## Precedence and reading order

`../base/CONSTITUTION.md` (binding, wins over everything) → `BIBLE.md` (durable decisions and
invariants) → `../razbiram-nlp/docs/razbiram-ECOSYSTEM.md` (family contract) → `AGENTS.md` (hard
rules — read before any substantive change) → newest `HANDOFF.md` entry →
`docs/architecture/SOLUTION_ARCHITECTURE.md` → relevant `docs/decisions/`. A local override of the
Constitution requires a dated amendment in `BIBLE.md`.

## Commands

```bash
./scripts/state.sh              # ground truth: branch, dirty files, ahead/behind, newest HANDOFF
./scripts/gate.sh               # the hard gate — must print "GATE: PASS" before work is done
./scripts/secure.sh             # everything committed and pushed?
./scripts/budget.sh             # token/LOC ratchet;  --update re-baselines (+5%)
./scripts/session-snapshot.sh   # emits a HANDOFF.md entry skeleton
./scripts/context.sh            # real context usage of this session, read from the transcript
```

`gate.sh` auto-detects surfaces: Python checks only if `pyproject.toml` exists, web checks only if
`package.json` exists (preferring `npm run verify:ci` when defined), plus shellcheck on every
tracked shell script, the budget ratchet, and secret/name scans. `.github/workflows/ci.yml` calls
the same script, so CI and local cannot drift — adding an implementation surface activates its
checks with no CI edit.

**Ratchet trap:** `.budget` caps the always-loaded doc footprint (`CLAUDE.md`, `AGENTS.md`,
`BIBLE.md`, `HANDOFF.md`, `README.md`, `docs/*.md`) at `DOC_TOKENS_MAX`. Growing any of those can
fail the gate. Trim elsewhere first; raise a ceiling only in a dedicated commit, never to silence a
regression (CONSTITUTION §4).

`scripts/namen-*.sh` and `scripts/meisterklasse-check.sh` are generic `dev/base` backbone scripts
for book repos and do not apply here — but the gate's shellcheck still covers them.

## Architecture in one pass

Two intake channels converge before extraction and never fork extraction, review, or export logic:
the standalone studio (screenshot / PDF / pasted text / `.razcapture` bundle) and a separately
downloaded Chrome/Firefox extension capturing the user-authorized active tab.

Both produce `ingest-envelope.v1` → `capture-ir.v1` (lossless card semantics + field-level evidence
+ review state) → deterministic validation → human review → reviewed-deck projection → export
profiles (native `studywithme-bg.learncard.v1`, or razbiram-anki for `.apkg`). Stages: Intake →
Scope → Capture/group → Detect → Extract → Join evidence → Normalize → Validate → Review → Export
(`docs/architecture/PIPELINE.md`).

Planned stack: Python 3.11+ core (loopback FastAPI service, Pydantic 2, SQLite, Playwright as
fallback only), React 19 + Vite studio, browser-neutral TypeScript extension core with Chromium MV3
and Firefox packaging. Proposed tree, dependency direction, API and CLI surfaces:
`docs/architecture/REPOSITORY_BLUEPRINT.md`. Dependency rule: no extractor imports an exporter, no
target-specific field appears in capture code, the extension imports only generated contracts.

Contracts with worked JSON: `docs/architecture/DATA_CONTRACTS.md` and `docs/schemas/`. Capture IR
stays private to this repo; razbiram-anki is reached only through the proposed versioned
`razbiram.recall-deck.v1` family contract, after review.

## Easiest invariants to violate

Full list in `AGENTS.md` and `BIBLE.md`. The ones a plausible-looking change breaks first:

- Multiple-select is lossless or blocked — never collapsed to single-choice, never a
  semicolon-joined string; export is gated on the target declaring the capability.
- True/false stays its own IR family and becomes a two-option MCQ only at export.
- Never write a correct answer the source did not prove or a reviewer did not confirm.
- Extraction may be automatic; export never is.
- IDs are deterministic (`captureId`, `sourceId`, `optionId`, `cardId`) — reformatting must not
  remint them.

## Session discipline

Start with `./scripts/state.sh` and `./scripts/gate.sh`; facts from the deterministic backbone come
before agent reasoning. End with a newest-first `HANDOFF.md` entry, durable decisions in
`BIBLE.md`, a green gate, granular Conventional Commits, push, and `./scripts/secure.sh`.

Substantive findings use the Base evidence protocol: claim → exact file/line evidence →
interpretation → counter-check → scoped action.
