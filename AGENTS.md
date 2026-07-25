# Agent instructions

The binding foundation is `../base/CONSTITUTION.md`. It wins over this file and every
repo/family briefing unless `BIBLE.md` records a deliberate dated amendment.

Read these files before substantive work:

1. `../base/CONSTITUTION.md`
2. `BIBLE.md`
3. `../razbiram-nlp/docs/razbiram-ECOSYSTEM.md`
4. the newest `HANDOFF.md` entry
5. `docs/architecture/SOLUTION_ARCHITECTURE.md`
6. the decision records relevant to the change

Run `./scripts/state.sh` and `./scripts/gate.sh` before substantive implementation. Facts from
the deterministic backbone come before agent reasoning.

## Hard rules

- Preserve evidence. Never invent a correct answer that the source did not prove or a reviewer
  did not confirm.
- A source screenshot and its hashes are local review evidence, not deck content by default.
- Multiple-select is lossless or blocked. Never downgrade it to single-choice.
- Use existing razbiram card types and product adapters for matching, typed, flashcard, and
  image occlusion.
- Treat true/false as a semantic source type and a compatible two-option MCQ at export.
- No crawling, hidden APIs, CAPTCHA bypass, DRM circumvention, or automatic access escalation.
- Browser automation is bounded by a declared source policy and explicit user action.
- Standalone and extension adapters converge before extraction; do not duplicate card logic.
- Keep Capture IR private to screen-to-learn. razbiram-anki integration begins only after review
  through the versioned family reviewed-deck contract.
- Never use CrowdAnki `deck.json` as the universal deck schema or silently flatten unsupported
  card families for Anki.
- Apply `dev/base` Rule of Three: do not extract a shared Anki implementation package for only
  razbiram-anki and screen-to-learn.
- Extension permissions are minimum and just-in-time: no cookies/history/debugger/`<all_urls>` by
  default, and no silent background observation.
- Treat uploaded files, PDFs, extension messages, and `.razcapture` archives as untrusted.
- Secrets come from environment/OS credential storage, never tracked files, URLs, logs, capture
  manifests, or frontend persistence.
- Local-first and no captured-content/origin telemetry. Brand discovery must not become
  surveillance, forced sign-in, or advertising inside exported cards.
- UI uses the versioned razbiram design tokens, supports light and dark, provides 44 px touch
  targets, and meets WCAG 2.2 AA.
- New LLM/heuristic behavior requires a Golden-Set case and deterministic schema validation.
- Keep source files under 500 lines; split by domain.
- README and code are English. Add German stakeholder/teacher documentation as `*.de.md`.

## Planned verification gates

`./scripts/gate.sh` is the root source of truth. As implementation surfaces are added, it runs:

- frontend lint, typecheck, tests, token/LOC checks, and build;
- backend ruff, pyright, pytest, and schema tests;
- Golden-Set regression tests without network access;
- Chrome/Firefox manifest, permission, bundle, and protocol parity tests;
- secret scanning and dependency audit.

No generated deck is “ready” while a blocking evidence, schema, safety, or capability issue
remains.

Substantive findings use the Base evidence protocol: claim → exact file/line evidence →
interpretation → counter-check → scoped action.
