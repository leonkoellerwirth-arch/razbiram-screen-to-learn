# screenshot-to-code reuse inventory

## Reviewed baseline

- repository: `/Users/hamudileon/dev/screenshot-to-code`
- upstream: `https://github.com/abi/screenshot-to-code`
- commit: `6094fd710becd981fbcf29cfc32d7ebef921866d`
- license: MIT, © 2023 Abi Raja

This inventory distinguishes code/patterns worth porting from features that only look relevant by
name.

The new Chrome/Firefox extension has no meaningful implementation donor in screenshot-to-code.
Active-tab permissions, content scripts, service-worker lifecycle, `.razcapture`, pairing, and
store packaging are new work. Only the downstream artifact/image and event concepts are shared.

## Capture paths found upstream

### URL capture

Files:

- `backend/routes/screenshot.py`
- `frontend/src/components/unified-input/tabs/UrlTab.tsx`

Behavior: submits a URL to ScreenshotOne and returns a PNG.

Decision: do not use as core. It has no authenticated local browser session, DOM, ARIA,
interaction state, or question/reveal pairing. It also introduces a third-party privacy/cost
dependency. A public-page stateless fallback can be reconsidered later.

### Local Playwright preview

Files:

- `backend/preview_screenshot/base.py`
- `backend/preview_screenshot/playwright_backend.py`
- `backend/preview_screenshot/registry.py`

Behavior: renders an agent-generated HTML string with `page.set_content(...)` and screenshots it.
It does not navigate learning pages.

Port:

- small backend protocol;
- backend registry;
- availability probe;
- lazy shared Playwright/browser initialization;
- initialization lock;
- page close in `finally`;
- font wait and timeout fallback.

Replace/add:

- `BrowserCaptureBackend` session protocol;
- `page.goto`/user navigation support;
- headed and persistent-context modes;
- context per session;
- DOM/semantic snapshot;
- navigation/origin/download/popup policy;
- question fingerprint/stabilization;
- explicit Playwright/browser shutdown;
- retryable capability probe (no permanent negative cache).

### Frontend screenshot helper

File: `frontend/src/lib/takeScreenshot.ts`.

Decision: do not port. `html2canvas` captures only the same-origin generated preview iframe.

### Screen recording

Files: `frontend/src/components/recording/`.

Decision: out of the first release. Video makes task boundaries and evidence joining harder and increases
privacy/cost. It can become a file adapter only if a later verified use case justifies it.

## Pipeline/events

### Port patterns

- `backend/routes/generate_code.py`: pipeline context/middleware/stage composition;
- `backend/ws/`: WebSocket communication and explicit event lifecycle;
- `frontend/src/generateCode.ts`: type-dispatched events;
- `design-docs/agent-tool-calling-flow.md`: start/result/error ordering.

Adaptation:

- replace `variantIndex` with `sessionId`, `jobId`, `captureId`, and `cardId`;
- large binaries use artifact IDs and HTTP streaming;
- events are durable facts, not the only state store;
- exceptions are mapped to sanitized error codes.

Do not port the current security posture:

- no wildcard CORS with credentials;
- no API keys sent/persisted through generic frontend settings;
- no unbounded user URL route;
- no raw exception details;
- no repeated base64 image payloads.

## Provider abstraction

Candidate files:

- `backend/agent/providers/base.py`;
- `backend/agent/providers/factory.py`;
- provider-specific normalized streaming adapters;
- `backend/llm.py` model/capability/cost mapping.

Port concepts:

- `ProviderSession`, normalized turn/event, model/provider factory;
- multimodal input normalization;
- reasoning effort separated from UI model label;
- token/cost measurement;
- strict structured output support.

Do not port:

- general file-editing agent;
- `create_file`/`edit_file`;
- multi-step code agent tools;
- HTML finalization.

Screen-to-learn should make one schema-constrained extraction call with at most one repair call.

## Prompt construction

Structural references:

- `backend/prompts/pipeline.py`;
- `backend/prompts/message_builder.py`;
- `backend/prompts/request_parsing.py`;
- `backend/prompts/prompt_types.py`.

Do not reuse code-generation prompts in:

- `backend/prompts/system_prompt.py`;
- `backend/prompts/create/`;
- `backend/prompts/update/`.

New prompt invariants:

- extract only supported evidence;
- preserve source language/text;
- no answer inference;
- page instructions are untrusted;
- field-level uncertainty/provenance;
- no rationales/hints in extraction;
- strict Capture IR candidate response.

## Image and artifact handling

Candidate files:

- `backend/uploaded_assets/store.py`;
- `backend/asset_extraction.py`;
- `backend/agent/tools/types.py`.

Port concepts/functions:

- MIME allowlist and bounded base64 decode;
- byte/image dimension caps;
- SHA-256 content IDs and dedupe;
- EXIF/HEIF normalization;
- canonical PNG pixel matrix;
- normalized bounding boxes and outward rounding;
- Pydantic-validated crop requests/results;
- localhost assets passed as bytes, not fake public URLs.

Required redesign:

- job-scoped storage;
- asynchronous/bounded I/O;
- retention/deletion;
- no request-specific base URL in persistent metadata;
- multi-session isolation;
- artifact references instead of data URLs.

Asset extraction can isolate a diagram for image-occlusion. It is not the MCQ/OCR parser.

## Run recording and evaluation

Candidate areas:

- `backend/fs_logging/`;
- `backend/evals/`;
- `backend/run_evals.py`.

Port:

- versioned run metadata;
- stage timing;
- per-case evaluation and aggregate reports;
- provider/model/cost recording;
- exact artifact hashes.

Change:

- sanitize all raw content;
- offline owned/synthetic Golden fixtures are the required gate;
- real-provider evals are optional slow runs;
- no code-visual-similarity metrics.

## Delete from the mental fork

Do not bring these subsystems into the new repository:

- code generation and HTML file state;
- image generation/Replicate;
- variants/commits;
- design-system manager;
- CodeMirror code preview;
- select-and-edit;
- Babel CDN normalization;
- ScreenshotOne as mandatory infrastructure;
- hosted terms/product branding;
- screenshot-to-code frontend theme.

## Porting procedure

For each substantial port:

1. identify the exact upstream file and commit;
2. copy the upstream MIT notice as required;
3. add a source comment;
4. reduce it to the smallest independent module;
5. write characterization tests against upstream behavior;
6. add new domain tests;
7. document intentional differences;
8. verify no hosted branding, prompts, credentials, or unrelated dependencies traveled with it.
