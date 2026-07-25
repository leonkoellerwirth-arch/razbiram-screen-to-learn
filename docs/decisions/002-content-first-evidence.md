# ADR 002 — Content-first evidence pipeline

- Status: accepted
- Date: 2026-07-25

## Context

Screenshots lose DOM roles, control state, labels, and source relationships. A question screenshot
often does not reveal the correct answer.

## Decision

Extract visible DOM/ARIA semantics first. Store a bounded screenshot crop as visual evidence and
use OCR/vision only as fallback/corroboration. Join question and reveal states. Only
source-verified or reviewer-confirmed answers can export.

## Consequences

- Cloud-free extraction works for accessible pages.
- Canvas/image-only sources require more review.
- A model's domain knowledge cannot silently fill an answer.
- Field-level evidence is a first-class contract.
