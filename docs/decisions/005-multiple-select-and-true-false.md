# ADR 005 — Multiple-select and true/false compatibility

- Status: accepted concept; platform capability pending
- Date: 2026-07-25

## Context

Razbiram already implements single-choice, matching, typed, flashcard, and image-occlusion
learning logic. The current MCQ runtime stores one selected string and compares it to one correct
string. Some content marks multiple options correct, but it is not correctly evaluated.

## Decision

- True/false remains a semantic Capture IR family and exports to the existing MCQ renderer with
  exactly two options plus `sourceFormat: "true-false"`.
- Multiple-select stores stable option IDs, a set of correct option IDs, and a scoring mode.
- Multiple-select export is blocked until razbiram.com declares and tests a coordinated
  capability with set-based selection, explicit Submit, and scoring.

## Consequences

- True/false needs a validator exception, not a new learning renderer.
- No semicolon-joined or first-answer downgrade is allowed.
- Existing multiple-correct content becomes a product regression target.
- Final contract naming remains owned by the product/shared schema decision.
