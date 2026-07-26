# 009 — Where extraction logic lives, now that there are two intakes

**Status:** open — decision required before either side writes more extraction code
**Date raised:** 2026-07-26
**Companion:** `razbiram.com/docs/architecture/capture-ingest-plugin-2026-07-26.md`

## Context

Until 2026-07-26 this repo was the only intake: capture a learning screen, extract cards, review,
export deck JSON. On the same day the owner decided razbiram.com gets its **own** standalone,
client-side capture plugin — screenshot / PDF / pasted text in, `studywithme-bg.learncard.v1` out.
That decision is recorded in both BIBLEs.

Both intakes must do the same five things: segment source material into question blocks, decide
each block's card family, bind the answer key without ever inferring it, assemble the deck, and
validate it. Today that logic exists here in Python (`extract.py`, `detect.py`, `validators.py`,
`identity.py`) and is planned there in TypeScript (`segment.ts`, `detectFamily.ts`,
`bindAnswers.ts`, `emitDeck.ts`).

**The duplication is real and not yet decided.** Writing it twice means every rule — every
normalization step, every family heuristic, every answer-binding edge case — has to be got right
twice and then kept in step forever. The family has paid this bill before: razbiram-listen's BIBLE
records a hand-kept `contract.py` mirror as a thing to be removed, not a pattern to repeat.

## What is already shared, and is not in question

`docs/schemas/learncard-target.v1.schema.json` is the single output shape both intakes emit.
`docs/schemas/card-detection.vectors.json` is the shared conformance suite for how a card's shape
is recognised. Those hold under every option below. The question is only about the *code that
produces* that output.

## Options

### A — One TypeScript package, consumed by both

Extraction moves to a shared TS package. razbiram.com imports it directly; this repo's browser
extension already runs TypeScript, and the Python core would call it or be retired.

- Rules exist once. A fix lands for both intakes at the same moment.
- Costs: today's Python extractor becomes throwaway work. It also creates a code dependency between
  the repos, which both BIBLEs currently forbid — "neither imports the other's code". That is an
  amendment, not a detail.
- The Base Rule of Three applies: two consumers is exactly the case where a shared package is
  usually premature.

### B — Two implementations, held together by the vectors

This repo keeps its Python core, studio and extension. razbiram.com writes its own client-side
plugin per its design. Neither imports the other. Drift is caught by both sides running the same
committed conformance vectors in their own CI.

- No coupling, no amendment needed; each side stays free to move.
- Costs: the same rules are written twice, and the vectors only catch divergence in what they
  cover. Segmentation quality — the hardest part, and the one razbiram.com's own design flags as
  "unproven" — is not covered by vectors at all.

### C — Split by responsibility, not duplicated

razbiram.com owns the thin path it designed: pasted text and PDF text layer, client-side, no
install. This repo owns what only it can do: the browser extension, live-DOM capture with the
question↔reveal join, the evidence ledger and the review flow. The overlap is then only the deck
assembly, which is already schema-driven.

- Each rule still has one home; the vectors keep the small shared surface honest.
- Costs: the boundary has to hold under pressure. The first time razbiram.com wants screenshot OCR
  (its Phase C), it re-enters this repo's territory and the question returns.

## Recommendation

**C, with B as the fallback.** The intakes genuinely differ in kind — one is a zero-install text
path, the other is an evidence-preserving capture pipeline with a browser extension — and the thing
that must not diverge (the output shape and the shape-detection rule) is already specified and
covered by shared vectors. A shared package (A) buys less than it costs at two consumers and would
require amending the no-code-dependency rule in both BIBLEs.

## Consequences of deciding late

Every week both sides write extraction code is a week of rules to reconcile later. This is worth
deciding before razbiram.com's Phase A lands, not after.

## Open until decided

No further extraction code is written on either side beyond what already exists.
