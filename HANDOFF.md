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

---

Older entries: `docs/handoff-archive/`.
