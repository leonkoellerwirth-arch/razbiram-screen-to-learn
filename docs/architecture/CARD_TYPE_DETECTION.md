# Card-type detection

A deck produced by razbiram-screen-to-learn arrives at razbiram.com the same way any other deck
does: uploaded, or pulled from a content repository. Nothing is configured per deck and nothing
announces "this came from screen-to-learn". The engine must therefore work out what each card is
**from the card itself**.

This document is the rule for doing that. It is written so the engine can implement it directly;
`docs/schemas/learncard-target.v1.schema.json` is the machine-checkable form and
`docs/schemas/card-detection.vectors.json` is a conformance suite to test an implementation
against.

## The rule

Apply in order. The first match wins. Every step reads only fields on the card.

| # | Condition | Detected mode |
|---|---|---|
| 1 | `type` is `"flashcard"` | `flashcard` |
| 2 | `type` is `"typed"` | `typed` |
| 3 | `type` is `"matching"` | `matching` |
| 4 | `type` is `"image-occlusion"` | `image-occlusion` |
| 5 | `type` is `"mcq"` and `selectionMode` is `"multiple"` | `mcq-multiple` |
| 6 | `type` is `"mcq"` and `sourceFormat` is `"true-false"` | `mcq-true-false` |
| 7 | `type` is `"mcq"` | `mcq-single` |
| 8 | anything else | `unknown` |

Steps 5 and 6 cannot both match: a card carrying both markers is invalid and the schema rejects it.
Order between them is therefore not load-bearing — it is fixed only so two implementations cannot
disagree.

## Why the markers are explicit

An engine could try to infer the shape: two options means true/false, more than one `isCorrect`
means multiple-select. Both inferences are wrong in ways that are hard to see.

- A genuine single-answer question may legitimately have two options.
- A multiple-select card whose author marked only one option correct is still a multiple-select
  card — the learner must still be able to select more than one, and scoring is still
  all-or-nothing.

Counting options answers a different question than the one being asked. The markers make the shape
a declaration rather than a guess, which is also what lets the 3–5 option rule keep applying to
plain MCQ while true/false carries exactly two.

## `unknown` must never render

Step 8 exists because new formats will be added again. An engine that falls back to "render it as
MCQ" turns an unrecognised card into a plausible-looking wrong one — the learner sees a question
that scores incorrectly and has no way to know. Treat `unknown` as a load error for that card:
skip it, and surface it in the deck's issue list.

This is the same reason the exporter blocks a card it cannot represent instead of degrading it.

## Interaction with runtime answer-mode promotion

The runtime may promote an MCQ card to typed recall. That promotion must not apply to
`mcq-multiple`: a card with several correct answers has no single string to type, and a typed
prompt would mark a correct learner wrong.

The format already prevents this by construction. A multiple-select card **omits `correctAnswer`
entirely** — its answer is the `correctOptionIds` set. Any eligibility check that requires a
non-empty `correctAnswer` therefore excludes it without needing a new rule. Keep that property:
do not synthesise a `correctAnswer` for multiple-select by joining option texts.

`mcq-true-false` may be promoted or not, as the product prefers — typing "True" is possible but
adds little. That is a product decision, not a correctness one.

## Answer semantics per mode

| Mode | Where the answer lives | Scoring |
|---|---|---|
| `mcq-single` | `correctAnswer`, equal to the text of the one option with `isCorrect: true` | one of N |
| `mcq-true-false` | `correctAnswer`, equal to one of the two option texts | one of two |
| `mcq-multiple` | `correctOptionIds`, equal to the set of options with `isCorrect: true` | `scoring.mode` — `all-or-nothing` or `partial-credit` |
| `flashcard` | `back` | self-assessed |
| `typed` | `acceptableAnswers` | any acceptable answer |

For `mcq-multiple` the option ids are authoritative, not the option order and not the text. Options
carry a stable `optionId` precisely so the answer set survives shuffling and re-wording.

## Localised text

`question`, `front`, `back` and `description` are language-keyed objects. `hint` and `explanation`
may be either a language-keyed object or a plain string — shipped decks use both, and the product's
own `LearnCard` type allows both. A parser must accept either.
