/**
 * The guarantee this app exists to keep.
 *
 * The whole point of the studio is that a human reviews evidence-backed cards before anything is
 * exported. A UI that hid a blocked card, or let one read as exportable, would quietly defeat
 * that — so it is asserted here rather than left to visual inspection.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CardList } from "./CardList";
import type { Card, ProcessExport } from "./types";

const localised = (text: string) => ({ value: { en: text }, evidence: ["ev_1"], confidence: 1 });

const card = (id: string, family: Card["family"], prompt: string): Card =>
  ({
    draftId: `draft_${id}`,
    cardId: id,
    sourceId: `src_${id}`,
    family,
    prompt: localised(prompt),
    review: { status: "needs-review", blockingReasons: [], reviewedBy: null, reviewedAt: null },
    rights: { basis: "user-authored", licenseNotes: null, approvedForPublication: false },
    answerEvidenceTier: "source-verified",
    options: [
      { optionId: "opt_a", text: "Alpha", isCorrect: true, evidence: ["ev_a"] },
      { optionId: "opt_b", text: "Beta", isCorrect: false, evidence: ["ev_b"] },
    ],
    correctOptionIds: ["opt_a"],
  }) as Card;

const CARDS = [
  card("q-ok", "single-choice", "Which medium is fastest?"),
  card("q-blocked", "multiple-select", "Select all that apply"),
];

const EXPORT_INFO: ProcessExport = {
  deck: { schemaId: "studywithme-bg.learncard.v1", meta: { cardCount: 1 }, cards: [] },
  blockedCardIds: ["q-blocked"],
  blocked: [
    {
      cardId: "q-blocked",
      family: "multiple-select",
      reason: "target does not declare mcq.multiple-select.v1",
    },
  ],
} as unknown as ProcessExport;

describe("CardList", () => {
  it("shows every card, blocked ones included", () => {
    render(<CardList cards={CARDS} exportInfo={EXPORT_INFO} />);
    expect(screen.getByText("Which medium is fastest?")).toBeDefined();
    expect(screen.getByText("Select all that apply")).toBeDefined();
  });

  it("marks a blocked card as blocked", () => {
    render(<CardList cards={CARDS} exportInfo={EXPORT_INFO} />);
    expect(screen.getByText(/BLOCKED/)).toBeDefined();
  });

  it("gives the reason a card was blocked, not just the fact", () => {
    render(<CardList cards={CARDS} exportInfo={EXPORT_INFO} />);
    expect(screen.getByText(/mcq\.multiple-select\.v1/)).toBeDefined();
  });

  it("does not mark an exportable card as blocked", () => {
    render(<CardList cards={[CARDS[0]]} exportInfo={{ ...EXPORT_INFO, blockedCardIds: [], blocked: [] }} />);
    expect(screen.queryByText(/BLOCKED/)).toBeNull();
  });
});
