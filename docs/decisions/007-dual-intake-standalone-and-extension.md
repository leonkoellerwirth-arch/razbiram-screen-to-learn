# ADR 007 — Dual intake: standalone studio and browser extension

- Status: accepted
- Date: 2026-07-25
- Supersedes: ADR 004 as the sole MVP intake decision

## Context

Students may already have a question open in Chrome or Firefox, but they also need to convert
screenshots, PDFs, and text without browser automation. Requiring a separate controlled browser
creates login friction; putting the entire pipeline into an extension duplicates complex logic
and weakens review, storage, and provider security.

## Decision

Build two first-class intake surfaces around one versioned core:

1. a standalone local studio for screenshot, PDF, text, `.razcapture`, and controlled-browser
   input;
2. a downloadable Chrome/Firefox WebExtension for explicit active-tab capture.

The extension offers:

- paired mode, forwarding evidence to the local studio;
- Capture Lite, downloading a portable `.razcapture` bundle when the studio is unavailable.

Both paths converge before extraction and produce `capture-ir.v1`. The extension owns capture
UX, permission handling, sanitization, and transport only. The standalone core owns extraction,
provider access, review, validation, and Razbiram export.

The controlled Playwright browser remains a fallback and deterministic testing adapter, not the
mandatory product entry point.

## Consequences

- Users can get value without installing both components.
- Normal-browser login state stays in the browser; credentials are never copied to the app.
- Chrome and Firefox require packaging, signing, permission-review, and cross-browser tests.
- A versioned `.razcapture` and pairing protocol become public compatibility boundaries.
- The project carries more distribution work but avoids two semantic pipelines.
- Extension discovery can support the Razbiram brand, subject to the no-surveillance/no-forced-
  account product invariant.

## Rejected alternatives

- **Extension only:** poor fit for large PDFs, bulk screenshots, rich review, provider secrets,
  and offline project organization.
- **Standalone controlled browser only:** avoidable authentication friction and lower
  discoverability.
- **Hosted upload service by default:** unnecessary privacy, account, storage, and compliance
  burden.
- **Native desktop screen recorder first:** broader permissions and weaker DOM evidence than an
  active-tab extension.
