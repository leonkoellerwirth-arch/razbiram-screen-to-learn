# ADR 004 — Bounded controlled-browser capture

- Status: superseded as the sole MVP intake by ADR 007; retained as fallback/test design
- Date: 2026-07-25

## Context

The family contract forbids scraping and unofficial endpoints. Users still need authenticated,
interactive browser content captured with context.

## Decision

The controlled-browser adapter launches a visible, dedicated Playwright browser. The user performs authentication and
navigation. The default third-party policy observes only the current selected task container
while capture is visibly active. Automatic next-click recipes are restricted to owned or
permission-confirmed sources.

## Consequences

- No general crawler, hidden API reader, CAPTCHA/paywall/DRM bypass, or background monitoring.
- Chrome/Firefox extension intake is now defined by ADR 007. CDP attachment remains out of scope.
- A source policy is mandatory for every session.
- Dedicated profiles improve isolation but may require the user to log in again.
