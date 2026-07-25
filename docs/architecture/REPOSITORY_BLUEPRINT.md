# Repository blueprint

## Proposed tree

```text
razbiram-screen-to-learn/
├── AGENTS.md
├── BIBLE.md
├── HANDOFF.md
├── README.md
├── LICENSE
├── SECURITY.md
├── THIRD_PARTY_NOTICES.md
├── pyproject.toml
├── package.json
├── start.sh
├── apps/
│   ├── studio/                       React 19 + Vite + TypeScript
│   └── extension/
│       ├── chromium/                 Manifest V3 package
│       └── firefox/                  Firefox package
├── packages/
│   ├── extension-core/               browser-neutral capture/sanitize/queue
│   └── generated-contracts/          generated TypeScript protocol types
├── src/
│   └── razbiram_screen_to_learn/
│       ├── api/                      loopback HTTP/WebSocket
│       ├── capture/                  controlled-browser fallback
│       ├── cli/                      studio/capture/extract/validate/export
│       ├── contracts/                Pydantic models + JSON Schema generation
│       ├── export/                   target profiles/capability checks
│       ├── extract/                  DOM/OCR/vision extractors
│       ├── ingest/                   image/PDF/text/bundle adapters
│       ├── integration/              reviewed-deck + razbiram-anki handoff
│       ├── jobs/                     queue/state/cancellation
│       ├── pairing/                  extension transport + capability tokens
│       ├── review/                   decisions/audit
│       ├── security/                 origin/source/retention policy
│       └── storage/                  SQLite + artifact store
├── schemas/
│   ├── capture-ir.v1.json
│   ├── extension-capture.v1.json
│   ├── ingest-envelope.v1.json
│   ├── reviewed-deck.ref.json        pinned hub reference, never forked
│   ├── event-protocol.v1.json
│   └── validation-report.v1.json
├── fixtures/
│   ├── pages/                        owned synthetic HTML apps
│   ├── expected/                     exact IR/export JSON
│   └── SOURCES.md
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── extension/
│   ├── playwright/
│   └── golden/
├── scripts/
│   ├── gate.sh
│   ├── token-budget.*
│   └── loc-budget.*
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── design/
│   ├── evaluation/
│   └── schemas/
└── .github/
    ├── workflows/ci.yml
    ├── PULL_REQUEST_TEMPLATE.md
    └── CODEOWNERS
```

## Dependency direction

```text
input adapters ───┐
extension protocol├→ contracts → pipeline → review → export profiles
OCR/providers ────┤       ↑          ↑          ↑
storage ──────────┘       security/policy       target capability manifest

API/CLI/Studio depend on core services; core never depends on UI.
The extension depends only on generated contracts and extension-core; it never imports extraction
or exporter code.
```

No extractor imports an exporter. No target-specific field appears in browser capture code.
No razbiram-anki implementation is copied into the Python core; integration consumes a versioned
family contract or package.

## Proposed technology baseline

Backend:

- Python 3.11+;
- Pydantic 2;
- Playwright Python;
- FastAPI/Uvicorn;
- Click or Typer-compatible CLI;
- SQLite via standard/typed repository layer;
- Pillow for bounded image normalization;
- ruff, pyright, pytest.

Studio:

- React 19;
- TypeScript;
- Vite;
- Tailwind v4 with Razbiram token bridge;
- a small accessible component layer;
- Vitest and Playwright E2E.

Extension:

- TypeScript and WebExtension APIs;
- Chromium Manifest V3 and Firefox-specific generated manifests;
- browser-neutral capture core;
- Vitest unit/contract tests and Playwright extension fixtures;
- the minimum permission budget defined in `BROWSER_EXTENSION.md`.

Do not add a general agent framework. The pipeline is explicit stages and strict structured model
calls.

## Reuse plan

Selective attributed ports from screenshot-to-code:

| Upstream | New destination |
|---|---|
| `backend/preview_screenshot/base.py` | capture backend protocol concepts |
| `backend/preview_screenshot/registry.py` | capture backend registry/capability probe |
| `backend/preview_screenshot/playwright_backend.py` | browser startup/reuse seed only |
| `backend/agent/providers/base.py` | provider session/event interface concepts |
| `backend/agent/providers/factory.py` | provider factory/capability selection |
| `backend/uploaded_assets/store.py` | validated image decode/hash concepts |
| `backend/asset_extraction.py` | EXIF/pixel/crop/schema-output helpers |
| `backend/fs_logging/` | sanitized run recording |

Every port:

- names upstream file and reviewed commit in a source comment;
- retains the upstream MIT notice where substantial;
- removes screenshot-to-code product assumptions;
- receives new tests before functional extension.

## Configuration

Precedence:

1. CLI flags;
2. environment;
3. local config under the tool home;
4. safe defaults.

Secrets never appear in local JSON config. Use environment or OS keychain. The studio reports
provider availability without returning secret values.

## Local storage

```text
$RAZBIRAM_SCREEN_HOME/
├── state.sqlite3
├── profiles/<opaque-session-or-profile-id>/
├── jobs/<job-id>/
│   ├── manifest.json
│   ├── captures/
│   ├── crops/
│   ├── snapshots/
│   └── exports/
├── extension-pairings/             revocable metadata, never page content
└── logs/                         sanitized metadata only
```

All IDs are validated opaque identifiers; no user path segment is interpolated.

## API surface

Minimal resources:

- `POST /v1/sessions`, `GET/DELETE /v1/sessions/{id}`;
- `POST /v1/ingest`, `POST /v1/ingest/{id}/artifacts`;
- `POST /v1/pairings`, `DELETE /v1/pairings/{id}`;
- `POST /v1/extension-captures`, `POST /v1/extension-captures/{id}/commit`;
- `POST /v1/sessions/{id}/browser`, `POST /pause`, `POST /capture`;
- `GET /v1/jobs/{id}`, `DELETE /v1/jobs/{id}`;
- `GET/PATCH /v1/cards/{id}`, `POST /approve`, `POST /reject`;
- `POST /v1/exports`, `GET /v1/artifacts/{id}`;
- `GET /v1/capabilities`;
- `/v1/events` WebSocket.

State-changing requests require the per-launch capability token and origin checks.

## CLI surface

```text
razbiram-screen-to-learn studio [--no-open] [--port 0]
razbiram-screen-to-learn import <image-pdf-text-or-razcapture>
razbiram-screen-to-learn capture --session <id>
razbiram-screen-to-learn extract <capture-manifest>
razbiram-screen-to-learn validate <capture-ir-or-deck>
razbiram-screen-to-learn export <capture-ir> --target razbiram
razbiram-screen-to-learn export <capture-ir> --target reviewed-deck
razbiram-screen-to-learn doctor
```

Studio and CLI call the same service/core functions.
