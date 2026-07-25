# ADR 006 — Current Razbiram Momentum identity

- Status: accepted
- Date: 2026-07-25

## Context

Sibling tools contain useful flow patterns but also token, dark-mode, icon, i18n, and
accessibility drift. The live product Corporate Identity has evolved.

## Decision

Use razbiram.com's current live theme/UI tokens, BrandMark, icon contract, and Momentum semantics
as authority. Propose shared versioned tokens because this is now another consumer; until then,
vendor an attributed commit-pinned snapshot with contract tests.

## Consequences

- screenshot-to-code UI is not reused.
- Older sibling CSS is reference only.
- Dark is default, light is respected, UI strings are localized, and controls meet 44 px/WCAG
  requirements from the first implementation.
- Theme/icon assets retain the © razbiram.com license carve-out.
