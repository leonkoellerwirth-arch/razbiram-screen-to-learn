# Browser capture design

## Capture modes

### 1. Chrome/Firefox extension

The extension captures the explicitly authorized active tab in the student's existing browser.
It sends a sanitized DOM/ARIA snapshot plus visible screenshot to a paired studio or downloads a
portable `.razcapture` bundle.

Advantages:

- no second login or separate browsing profile;
- strong semantic evidence from the page;
- low-friction, downloadable Razbiram product surface;
- Capture Lite remains useful without the standalone app.

Constraints:

- temporary active-tab permission is the default; observe mode requires a narrow origin grant;
- the screenshot API sees the visible viewport, not arbitrary hidden content;
- extension stores and browser differences add release work;
- the page still has to reveal a correct answer or the reviewer must confirm it.

The complete permission, transport, packaging, and acquisition design is in
[BROWSER_EXTENSION.md](BROWSER_EXTENSION.md).

### 2. Controlled Playwright browser — fallback and test adapter

The tool launches visible Chromium with a dedicated profile. The user performs login, MFA, and
navigation directly. The tool observes only while a capture session is visibly active.

Advantages:

- stable browser API;
- full DOM and screenshot access;
- isolated cookies/profile;
- deterministic test fixtures;
- no broad extension permission.

Constraints:

- it is a separate browser profile;
- some managed platforms may block automation;
- CAPTCHA remains a user interaction and is never bypassed.

### 3. File/import adapter

Static screenshots, PDFs, and text supplied by the user enter the same artifact contract. This
path has weaker structure and therefore a higher review requirement. See
[INPUT_CHANNELS.md](INPUT_CHANNELS.md).

## Source policy

Each session declares one policy:

| Policy | Navigation | Automatic observation | Automatic next-click |
|---|---|---|---|
| `user-upload` | local fixture/file | yes | n/a |
| `first-party-owned` | allowlisted origin | yes | only with explicit bounded recipe |
| `permission-confirmed` | allowlisted origin | yes | only with documented permission |
| `third-party-observe` | user navigation only | current task container only | never |

The default is `third-party-observe`.

No policy permits hidden APIs, credential capture, CAPTCHA/DRM/paywall bypass, or access beyond
what the user can visibly open.

## Capture bundle

One stable page state produces:

```text
capture manifest
├── sanitized URL (scheme + host + path; no credentials/query/fragment)
├── title, viewport, locale, timestamp
├── semantic snapshot
│   ├── visible normalized text
│   ├── roles/names/states for relevant controls
│   ├── local stable node references
│   └── bounding boxes
├── question-container PNG
├── optional full viewport PNG (private, short retention)
├── resource/console diagnostics (redacted, opt-in)
└── SHA-256 hashes
```

Do not store cookies, storage state, request headers, password fields, hidden form values,
authorization tokens, or raw page scripts.

## DOM/semantic snapshot

The injected capture function is deterministic and read-only:

- walks visible nodes under the selected/candidate container;
- records text from rendered nodes;
- resolves labels for radio/checkbox/button/input roles;
- records `checked`, `disabled`, `expanded`, and feedback-relevant attributes;
- records bounding boxes in normalized viewport coordinates;
- descends open shadow roots;
- treats cross-origin iframes as screenshot-only unless separately user-approved;
- strips scripts, styles, event handlers, URLs with query/fragment, and form values;
- caps nodes, depth, text length, and runtime.

The snapshot is data, never executable HTML.

## Question detection

Generic detection scores candidate containers using:

- a question-like text block;
- 2–8 radio/checkbox/button options;
- shared form/fieldset/list container;
- accessible group name/legend;
- visible submit/check control;
- geometry: question and options in one region;
- state changes after answer/reveal.

The user can select a container when generic detection is ambiguous. That selection creates a
session-local locator hint, not a hardcoded public-site scraper.

## State stabilization

A state is capturable when:

- DOM mutation rate stays below a threshold for 300–500 ms;
- fonts are ready or a timeout elapses;
- the candidate bounding box is stable;
- no blocking modal overlays the candidate;
- content fingerprint differs from the last accepted state, or its answer-state fingerprint
  changed.

Use debounce plus a maximum wait. Never wait on global `networkidle` alone; long-polling pages may
never become idle.

## Fingerprints

`questionFingerprint` is the cross-state join key. It hashes:

- NFC-normalized question stem text;
- NFC-normalized, **feedback-stripped**, **lexicographically sorted** option clean texts;
- card-family classification;
- sanitized origin and path scope.

Sorting before hashing makes the fingerprint order-independent (G13: options randomized between
question and reveal states still join correctly). Stripping feedback annotations before sorting
ensures reveal-state option texts (e.g. "✓ any set of related data") match their question-state
counterparts ("any set of related data"). The exact normalization, stripping rules, and
serialization are specified in [IDENTITY_ALGORITHMS.md](IDENTITY_ALGORITHMS.md).

`stateFingerprint` is the per-state dedup key. It extends `questionFingerprint` with:

- checked states and raw visible option texts (including any feedback labels);
- revealed explanation text.

The `stateFingerprint` is identical across React rerenders of the same semantic state (G14) and
distinct between the question and reveal states of the same question. It prevents duplicate
captures without blocking valid state transitions.

Both fingerprints are embedded in the `semantic-snapshot.v1` artifact and mirrored in the
`extension-capture.v1` manifest for fast grouping without opening the artifact.

## Answer-state pairing

The state machine stores all states for one question fingerprint:

```mermaid
stateDiagram-v2
    [*] --> Candidate
    Candidate --> QuestionCaptured: stable unanswered state
    QuestionCaptured --> AwaitingEvidence
    AwaitingEvidence --> RevealCaptured: visible feedback/solution
    AwaitingEvidence --> NeedsReview: user stops/no reveal
    RevealCaptured --> DraftReady: evidence agrees
    RevealCaptured --> NeedsReview: contradictory/ambiguous
```

A user's checked option before authoritative feedback is recorded as `user-selection`, not
`correct-answer`.

## Screenshot policy

- capture the smallest complete question container;
- add safe padding;
- capture full viewport only for debugging/review context;
- redact detected email/account/avatar/topbar regions when possible;
- never include browser chrome;
- normalize EXIF orientation and pixel format;
- store original and derived hashes;
- never embed full screenshots into a deck by default.

## Browser lifecycle

- one context per capture session;
- dedicated profile directory with restrictive permissions;
- explicit `Start capture`, `Pause`, and `Stop` controls;
- block unexpected downloads and pop-ups, surface them to the user;
- close pages/contexts on cancellation;
- shutdown hook terminates browser and Playwright cleanly;
- session wipe deletes evidence and optionally the dedicated profile;
- capability probe can be retried and does not permanently cache a failure.
