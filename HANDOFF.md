# HANDOFF — razbiram-screen-to-learn

Session handoffs, **newest entry first**. Written at session stop and read after the Base
Constitution and BIBLE at session start.

## 2026-07-27 — The recognised deck is always visible, and the gate moved to the backend

_gate PASS · 32 Python tests + 13 studio tests_

- **Done:**
  - **The review gap the entry below called "the next job" is closed.** The export panel showed the
    JSON editor only in its `deck !== null` branch, so a run reading `0 exportable · 3 blocked`
    rendered a red box and nothing else — cards recognised, no way to reach them. The editor is now
    always present and open, seeded with the export or with a draft.
  - **`draft.py`** projects every recognised card into target shape, blocked ones included, with the
    unevidenced parts left explicitly empty; **`check_deck`** applies the export path's own rules to
    hand-edited JSON, exposed as **`POST /v1/deck/check`**. The browser never judges validity — a
    second copy of the rules in TS is a second thing to keep true.
  - **`ExportPanel.tsx`** extracted out of `App.tsx`: draft/export toggle when both exist, blocked
    reasons named by their *draft* id, Download disabled until the backend clears the edit.
  - **A hole found by using it, not by testing it.** A true/false card blocked at tier
    `source-ambiguous` still carried the extractor's answer, so the draft was structurally complete,
    the gate cleared it, and Download turned green on an unevidenced answer. Fixed: an unqualified
    tier drafts as unanswered. Test: `test_an_unqualified_answer_is_stripped_rather_than_offered`.
  - **README shows a real run** — the same quiz with and without its key, real JSON, real gate
    messages — plus a Known limits section.
  - **`start.sh` is stated as the only way to start the app**, in its header, its `--help`, and
    `CLAUDE.md` (whose "no runtime code exists yet" status was several sessions stale).
- **Decided:** two BIBLE entries — the always-visible deck with a backend gate, and drafts never
  carrying an answer the export would refuse.
- **Open / next:**
  - **A question number OCR fails to read costs that question its answer key.** Measured on
    `fixtures/images/quiz.png`: OCR drops the `2` from question 2, blocks inherit the previous
    index, and the key row `2. A, C` binds to the wrong question — the metals card exported with one
    correct option instead of two, silently. The key parser itself is correct; the pasted-text path
    resolves `A, C` as expected. **This is the next job**: an inherited index must not bind a key.
  - `App.tsx` still resets the edited JSON when a second file arrives (unchanged from below).
  - Highlighted rows still read badly; band re-reading still unbuilt.
- **Continuity warnings:**
  - The fixture test asserts three exportable cards from `quiz.png`. Fixing the index-inheritance
    bug will change that expectation — the metals card should block, not export a wrong answer.
  - `.budget` moved again, in its own commit; `draft.py` and the README example are what grew.

## 2026-07-26 — Images become cards: the drawn-structure reader, honest progress, a review gap

_gate PASS · 159 tests_

- **Done:**
  - **Image intake works.** `ocr.py` (tesseract subprocess, no language choice), `layout.py` (word
    geometry from TSV), `screenshot.py` (structure from typography, widget tokens and colour),
    `textseg`/`textcards` (the lexical path). `process_image` runs both readings and keeps
    whichever yields more answerable blocks — selection by score, not by guess.
  - **Two real documents carried it.** A 2500×28662 practice quiz marking answers only in colour:
    0 → 19 cards, 14 with measured correctness, 11 exportable. A plain ISO-27001 sheet with
    `a.`/`b.`/`c.`: 2 shredded fragments → 3 complete questions.
  - **Honest progress.** `progress.py` + `/v1/process/stream` (NDJSON off a worker thread) +
    `ProgressPanel.tsx`. Real stages only; no proportion is shown that nobody measured.
  - **The JSON view is editable**; copy and download take the edited text, and invalid JSON
    disables download rather than handing over a file the target cannot read.
  - **`start.sh`** adopted from razbiram-anki; warns early when tesseract is missing.
  - **Two Fable reviews acted on.** Both said needs-work, not reimplement. Fixed from them: the
    exporter accepted unevidenced cards on its own (only the validator caught it, and nothing had
    produced a non-exportable tier until this session made it reachable); `{"und": …}` was
    hard-coded so every card would have rendered blank at the target; a long title produced a
    `deckKey` its own schema rejects; `.txt` uploads claimed `reviewer` evidence nobody gave.
- **Decided:** eight entries in the BIBLE register. Most consequential: **extraction now lives
  here**, superseding the same day's freeze, and **a local LLM is a fallback, never the
  structurer** — measured on the installed models, not assumed.
- **Open:**
  - **No review step in the studio UI.** Cards without an answer key are correctly left unbound and
    correctly refused by the exporter — but nothing lets a person set the answer, so a sheet
    without a printed key is extracted and then stuck. razbiram.com's ingest has radio buttons for
    exactly this. **This is the next job.**
  - Highlighted rows still read badly (`Therei h thi Sprint 0 in 5`). The fix is proven — crop the
    row away from its own chrome and re-read — but not built.
  - Multi-file upload and per-type size limits were asked for and are not built.
  - `App.tsx` resets the edited JSON when a second file arrives, discarding edits silently.
- **Next:** the review step, then band re-reading.
- **Continuity warnings:**
  - **The budget moved three times in one session** (SRC_LOC 1714 → 3436) plus once for docs
    (8600 → 9610). Each raise is argued in `.budget`; read that file before a fourth. Note also
    that "split instead" does not work — budget.sh totals every line under `src/`.
  - **`textseg`/`textcards` now diverge from razbiram.com's `segment.ts`/`classify.ts`**, which
    carry two bugs fixed here: plain text after an option run shreds wrapped answers, and
    true/false is demoted to single-choice when no key is present. ADR 009 is the reunion record.
  - **The studio serves a built bundle from a long-lived Python process.** Editing source changes
    nothing until `npm run build` plus a restart (`./start.sh --free-port`). This cost real
    confusion today — say it out loud when asking anyone to retest.

---

Older entries: `docs/handoff-archive/`.
