# ADR 003 — Capture IR separated from export profiles

- Status: accepted
- Date: 2026-07-25

## Context

Browser evidence, review state, and target-deck rendering have different owners and evolution
rates. Mapping directly from a screenshot into today's deck shape would lose multiple-select
semantics and couple capture to product internals.

## Decision

Introduce versioned `capture-ir.v1` as a lossless reviewed intermediate contract. Exporters map an
immutable approved snapshot into target profiles and enforce capability manifests.

## Consequences

- Multiple-select can be captured before the product supports it without corrupt export.
- Target contracts can evolve without rewriting browser capture.
- Migrations are required for breaking Capture IR changes.
- Raw evidence stays in a separate private sidecar.
