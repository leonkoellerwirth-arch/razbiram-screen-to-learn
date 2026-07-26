# Feasibility assessment

## Verdict

| Dimension | Assessment | Reason |
|---|---|---|
| Chrome/Firefox extension | Feasible | WebExtensions provide explicit active-tab scripting and visible-tab screenshots; Firefox needs a tested compatibility adapter. |
| Standalone screenshot/text input | High feasibility | Bounded local parsing plus OCR/vision fallback maps cleanly to one ingest contract. |
| PDF input | Feasible with constraints | Digital text layers are strong; scans, formulas, answer-key linking, and hostile PDFs require rendering limits and review. |
| Controlled-browser fallback | Feasible | Playwright supports headed profiles, DOM access, screenshots, events, and deterministic fixtures. |
| Authenticated pages | Feasible with constraints | The extension uses the user's existing session; controlled-browser login stays interactive. Credentials never enter the pipeline. |
| Single-choice extraction | High feasibility | DOM roles plus a visible reveal state are usually sufficient. |
| True/false | High feasibility | Semantic source classification plus two-option MCQ export. |
| Multiple-select | Extraction feasible; platform work required | Current razbiram MCQ state and scoring are single-answer only. |
| Existing card types | Feasible | Matching, typed, flashcard, and image-occlusion already have target logic; adapters need contract tests. |
| razbiram-anki handoff | Feasible with new adapter | Current app has proven CrowdAnki/APKG machinery, but it does not accept native Learn JSON or reviewed Capture IR. |
| Canvas/image-only pages | Medium feasibility | Requires OCR/vision and human review; exact text/formula fidelity is harder. |
| Fully automatic bulk conversion | Not approved as a default | It conflicts with evidence, source-policy, legal, and family no-scraping constraints. |
| Direct platform import | Not MVP-ready | No verified self-service route should be claimed. |

The correct outcome is a **conditional GO** for a review-first dual-intake tool. The condition is
not whether an extension is technically possible; it is whether M0 proves evidence quality,
Chrome/Firefox parity, safe pairing/bundles, and exact target compatibility.

## What can be reused from screenshot-to-code

Reviewed upstream commit:
`6094fd710becd981fbcf29cfc32d7ebef921866d`.

| Area | Reuse level | Notes |
|---|---:|---|
| Screenshot backend protocol/registry | High pattern reuse | Extend from render-only to browser-session capabilities. |
| Lazy Playwright lifecycle | Medium code reuse | Add contexts, persistent profile, navigation policies, shutdown, and capture snapshots. |
| FastAPI/WebSocket pipeline | Medium code reuse | Replace `variantIndex`/code events with job/session/capture/card events. |
| Provider session adapters | Medium code reuse | Keep normalized multimodal streaming/costs; remove file-editing agent behavior. |
| Pydantic structured vision output | High pattern reuse | Use strict card/candidate schemas. |
| Image validation/normalization/cropping | Medium-high code reuse | Make job-scoped, async-safe, and retention-aware. |
| Run recorder/evaluation layout | Medium pattern reuse | Record sanitized evidence and deterministic stage outcomes. |
| ScreenshotOne URL route | None for core | No authenticated DOM/session and creates a third-party privacy dependency. |
| `html2canvas` preview capture | None | Same-origin preview only. |
| Code generation prompts/tools | None | Wrong domain and unsafe over-capability. |
| Variants, CodeMirror code preview, Replicate | None | Not needed for learning-content extraction. |

Expected direct/conceptual reuse is roughly 20–30% of backend infrastructure, not 20–30% of the
whole application.

The extension itself is new WebExtension work. Screenshot-to-code does not supply active-tab
permissions, content scripts, extension packaging, offline capture bundles, or browser-store
distribution.

## razbiram-anki integration feasibility

Direct reuse is valuable at the approved export boundary:

- reuse `.apkg` writing, CrowdAnki construction, media packaging, stable identifiers, and the
  existing deck round-trip methodology;
- do not reuse CrowdAnki as Capture IR or as the native LearnCard schema;
- add a proposed hub-owned reviewed-deck contract and a razbiram-anki input adapter;
- capability-gate every Anki mapping.

Current blockers are architectural work, not fundamental feasibility:

- `razbiram-anki` is a Vite application with `private: true` and no public package exports;
- its input accepts `.apkg` or CrowdAnki JSON only;
- razbiram.com's CrowdAnki adapter handles MCQ, flashcard, and image occlusion, rejects
  multiple-answer all-in-one MCQs, and does not expose matching/typed through that path;
- the family hub currently defines `EnrichedDocument`, not a reviewed deck schema.

Conclusion: **GO for contract/file handoff; conditional GO for direct browser handoff and shared
code package after cross-repo Golden tests.**

## Evidence feasibility

### Strong evidence

- checked radio/checkbox state explicitly labeled as correct after submission;
- visible solution section;
- visible feedback associated with option IDs;
- user confirmation in the review UI;
- first-party structured content exposed through the visible page contract.

### Weak evidence

- color alone;
- a user's currently selected answer before feedback;
- handwriting/highlights;
- an LLM's domain knowledge;
- a semicolon-separated legacy `correctAnswer`;
- hidden application state that was not presented to the user.

Weak evidence cannot autonomously set a correct answer.

## Current platform facts

The current product:

- recognizes `studywithme-bg.learncard.v1` by deck metadata;
- supports `mcq`, `matching`, `typed`, `flashcard`, and `image-occlusion` in types/dispatch;
- stores one selected MCQ answer and compares it with one correct answer;
- does not consume MCQ `scoring.mode` for multiple selection;
- already contains a few multiple-correct cards that therefore render incorrectly.

These existing files are regression evidence, not a working compatibility contract.

True/false requires no new learning interaction. A two-option radiogroup works with the current
single-choice runtime; only validators that enforce 3–5 options need a declared exception.

## Principal feasibility risks

| Risk | Impact | Mitigation |
|---|---|---|
| Correct answer never becomes visible | Critical | Draft remains blocked; require user confirmation or a reveal capture. |
| DOM changes between source platforms | High | Generic ARIA extractor, small optional site profiles, screenshot fallback, Golden fixtures. |
| Page prompt injection | High | Treat all page data as untrusted; model has no general browser/file/shell tools. |
| Private data in full-page screenshots | High | Container-first crops, redaction, local retention, explicit provider consent. |
| Copyright/terms violation | High | Source policy, rights basis, no crawler, private fixtures, human publication gate. |
| Formula/image OCR errors | High | Preserve crop evidence, rich-text normalization, review zoom, exactness tests. |
| Duplicate/reordered questions | Medium | Stable fingerprints from normalized content and source scope. |
| Browser/profile compromise | High | Dedicated profile, loopback-only service, context isolation, download/popup policy. |
| Extension over-permission | High | `activeTab` by default, just-in-time named-origin grants, automated manifest permission budget. |
| Malicious `.razcapture` | High | Archive traversal/symlink rejection, schemas, hashes, media sniffing, and decode limits. |
| Pairing impersonation | High | Short-lived pairing, exact extension origin, capability token, loopback/Host checks, revocation. |
| Chrome/Firefox divergence | Medium | One neutral core, generated manifests, identical cross-browser Golden fixtures. |
| CrowdAnki used as universal schema | High | Shared reviewed-deck contract; native and Anki exporters remain siblings. |
| Anki semantic degradation | High | Capability matrix; block unsupported mappings until tested. |
| Cross-repo version drift | Medium | Hub schema version, generated types, compatibility matrix, pinned Golden fixtures. |
| Large/scanned PDF | Medium | Page selection, text-layer first, bounded rendering/OCR, cancellation, explicit limits. |
| Provider cost/latency | Medium | DOM-only fast path, bounded jobs, budget, local provider option, escalation model. |

## Proof-of-concept exit criteria

Proceed to product implementation only if M0 proves:

1. Chrome and Firefox produce semantically equivalent captures for an owned fixture;
2. `.razcapture` round-trips offline and paired transfer rejects invalid origin/token/hash;
3. screenshot, text, digital PDF, and scanned-PDF fixtures enter the same IR;
4. question and reveal states can be joined without reading hidden private APIs;
5. repeated React rerenders do not create duplicate captures;
6. true/false exports and renders as a correct two-option MCQ;
7. multiple-select is correctly extracted and blocked without target capability;
8. an existing flashcard and image-occlusion fixture round-trip through the target adapter;
9. cloud-disabled extraction still produces a valid compatible deck;
10. session deletion removes imported, browser, and extension-derived artifacts.

## M2A gate criteria — razbiram-anki handoff

Out of M0 scope. These require the hub-owned `razbiram.recall-deck.v1` contract and a razbiram-anki
import path, neither of which exists yet; they gate the M2A ecosystem milestone, not the M0 spike.

1. one reviewed-deck file hands off to razbiram-anki and round-trips a supported `.apkg`;
2. unsupported Anki families block without semantic degradation.
