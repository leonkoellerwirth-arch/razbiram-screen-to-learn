# ADR 008 — Integrate razbiram-anki at the reviewed-deck boundary

- Status: accepted as architecture; cross-repo contract work pending
- Date: 2026-07-25

## Context

`razbiram-screen-to-learn` and `razbiram-anki` should reinforce one ecosystem. The current
`razbiram-anki` application, however, accepts Anki/CrowdAnki structures, while screen-to-learn
captures richer evidence and targets native LearnCard JSON. Routing Capture IR through
CrowdAnki would lose evidence and unsupported card semantics.

## Decision

Keep Capture IR private to screen-to-learn. After review, project approved cards into a proposed
hub-owned `razbiram.recall-deck.v1` contract.

- screen-to-learn exports native razbiram Learn JSON directly;
- razbiram-anki consumes the shared reviewed deck and owns `.apkg`/CrowdAnki generation;
- file handoff is the first integration;
- an explicit exact-origin browser handoff follows after contract tests;
- reusable Anki code remains in razbiram-anki until a third real consumer satisfies the Base Rule
  of Three; file/direct handoff is used before then.

The new family contract requires a Mini-ADR in `razbiram-nlp`; it must not be presented as already
implemented.

## Consequences

- Students receive Razbiram and Anki outputs from one reviewed source.
- The ecosystem gains a shared semantic deck boundary without making CrowdAnki universal.
- Evidence, browser data, and review history do not leak into Anki packages.
- Card types are capability-gated independently for razbiram.com and Anki.
- `razbiram-anki` needs a new reviewed-deck input and canonical note models.
- Cross-repo schema/version and Golden-Set coordination become release requirements.

## Rejected alternatives

- **Import current razbiram-anki source files directly:** no stable package API and tight Vite-app
  coupling.
- **Use CrowdAnki deck.json as the shared contract:** cannot express all reviewed semantics or
  private evidence safely.
- **Send Capture IR to razbiram-anki:** exposes tool-specific/private capture state.
- **Put `.apkg` generation into screen-to-learn:** duplicates the Anki bridge and its fidelity
  tests.
