# HANDOFF — razbiram-screen-to-learn

Session handoffs, **newest entry first**. Written at session stop and read after the Base
Constitution and BIBLE at session start.

## 2026-07-26 — Leaked remote PAT, and a push blocker

_gate PASS · tree clean · **36 commits local-only**. The day's engineering is in
`git log d4d1837..HEAD` + `EXECUTION_PLAN.md`; not restated here by an agent who wasn't in it._

- **⚠ A live GitHub PAT sat in this repo's git remote URL** (found from the razbiram.com session;
  `git remote -v` printed it to that transcript, so treat it as disclosed). **Verified scope:**
  `.git/config` only — no tracked file, not in history, **no rewrite needed**; sibling repos clean.
  **Done:** remote is now token-free HTTPS (a global `gh` credential helper already existed).
  **Owner:** revoke that PAT — it was already 403-ing on push, so nothing depends on it.
- **BLOCKER — the 36 commits cannot be pushed.** The active `gh` account has `push: true` but
  lacks the **`workflow`** scope, and the range touches `.github/workflows/ci.yml`. SSH is no
  alternative (the local key is `HamudiLeon`, denied). **Fix:**
  `gh auth refresh -h github.com -s workflow` → `git push origin main`. Until then this repo's
  work exists on one disk — the same loss class flagged 2026-07-22 in razbiram.com, at 14 commits.
- **Next:** after the push, M0 — 31 done / 11 open (P5.2b/c, P5.3, P5.6–P5.10, two decisions).

## 2026-07-26 — M0 vertical slice, the two additive deck formats, razbiram.com Phases 1–3

_The engineering the entry above deliberately left to its author. gate PASS · tree clean._

- **Done:** Repaired the evidence-join contract three reviews found broken — sorted fingerprint
  (G13 could not have passed), required `captureState`/`stateFingerprint`, new
  `semantic-snapshot.v1`, `IDENTITY_ALGORITHMS.md`. Aligned the export contract with the shipped
  product (`access` not `accessTier`). Built the M0 slice: extract → validate → capability-gated
  export, a loopback studio API, and a React studio **adopted from razbiram-anki** rather than
  invented. Specified the two additive deck formats (`learncard-target.v1.schema.json`, reference
  example, `CARD_TYPE_DETECTION.md`, 15 conformance vectors) and **implemented them in
  razbiram.com** — branch `feat/learncard-multiselect-truefalse`, Phases 1–3 of its own design doc.
  127 tests here, 2979 there.
- **Decided:** Capabilities are read from a pinned copy of razbiram.com's profile and **fail
  closed**. Identifiers are `mcq.true-false` / `mcq.multiple-select.v1`; `mcq.two-option.v1` was
  invented by me and is gone. Owner: user data goes to an **org-owned private GitHub repo, one
  folder per user** — designed in `razbiram.com/docs/architecture/user-deck-github-storage-2026-07-26.md`,
  deliberately not built.
- **Open:** **ADR 009** (extraction logic about to exist twice — Python here, TypeScript there;
  urgent, razbiram.com's capture plugin is starting). §3 of the GitHub-storage design
  (repo-per-user vs folder-per-user) blocks its Phase A: it decides whether the token needs
  repo-delete rights, and git history makes "account deleted" a promise that is hard to keep.
- **Next:** ADR 009, then P5.6 — the extension fixture, i.e. the second entry channel.
- **Continuity warnings:**
  - **razbiram.com is left on `feat/learncard-multiselect-truefalse`** with ~18 uncommitted owner
    files (Tesseract OCR staging). I switched that branch while the owner was working in it.
  - Three `dev/base` gaps, all affecting siblings: `gate.sh` only saw `app/`-or-root web surfaces,
    so anything under `apps/` was skipped **in silence** (fixed here only); `budget.sh --update`
    raises both ceilings at once; hooks in `razbiram-listen`/`razbiram-nlp` are tracked but dormant.
  - razbiram.com carries 392 pre-existing tsc errors. Mine added none (stash-verified), but a bare
    `tsc --noEmit` there is not a usable signal.

---

Older entries: `docs/handoff-archive/`.
