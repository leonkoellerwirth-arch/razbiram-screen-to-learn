# ADR 001 — Selective upstream reuse and local runtime

- Status: accepted for M0
- Date: 2026-07-25

## Context

The project is inspired by screenshot-to-code and should reuse proven functions where sensible.
A wholesale fork would retain unrelated code generation, image generation, variants, hosted
product assumptions, and foreign UI identity.

## Decision

Create a new local Python service plus React studio and a small TypeScript WebExtension core with
Chrome/Firefox packages. Port only bounded MIT-licensed infrastructure
patterns/files with attribution: Playwright lifecycle seed, backend registry, provider
normalization, image validation/cropping, event pipeline, and run recording.

## Consequences

- Browser navigation, semantic snapshots, evidence joining, review, and Razbiram export are new
  domain code.
- The extension, `.razcapture`, and pairing protocols are new code, not screenshot-to-code ports.
- Upstream provenance is auditable in source comments and third-party notices.
- Python Playwright suitability is proven in M0. A runtime change requires revisiting this ADR,
  not adding a second orchestrator.
