/**
 * The panel's two duties, which pull in opposite directions.
 *
 * Show everything: a person who sees "0 exportable · 2 blocked" and no JSON has been told a card
 * exists and denied any way to look at it. Release nothing: what the extractor could not evidence
 * must not become a downloadable file just because it is now on screen. The first is a UI choice;
 * the second is BIBLE invariant 3, and it is enforced by the backend — these tests pin that the UI
 * actually asks, and believes the answer.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProcessExport } from "./types";

const checkDeck = vi.fn();
vi.mock("./api", () => ({ checkDeck: (deck: unknown, caps: string[]) => checkDeck(deck, caps) }));

const { default: ExportPanel } = await import("./ExportPanel");

const DECK = {
  schemaId: "studywithme-bg.learncard.v1",
  meta: { cardCount: 1 },
  cards: [{ cardId: "q-0001", type: "mcq", question: { en: "Which clause?" } }],
};

const DRAFT = {
  schemaId: "studywithme-bg.learncard.v1",
  meta: { cardCount: 2 },
  cards: [
    DECK.cards[0],
    { cardId: "q-0002", type: "mcq", question: { en: "Which audit clause?" }, correctAnswer: "" },
  ],
};

const exportInfo = (over: Partial<ProcessExport> = {}): ProcessExport => ({
  deck: DECK as ProcessExport["deck"],
  draft: DRAFT as ProcessExport["draft"],
  capabilities: ["mcq.true-false"],
  blockedCardIds: [],
  blocked: [],
  ...over,
});

const BLOCKED = [
  { cardId: "c-77", family: "single-choice", reason: "source-ambiguous", draftCardId: "q-0002" },
];

describe("ExportPanel", () => {
  beforeEach(() => {
    checkDeck.mockReset();
    checkDeck.mockResolvedValue({
      ok: false,
      errors: ["card q-0002: mark exactly one correct option"],
      deck: null,
      config: null,
    });
  });

  it("shows the JSON without anyone asking for it", () => {
    render(<ExportPanel exportInfo={exportInfo()} deckTitle="clauses" />);
    const editor = screen.getByLabelText("Deck JSON — editable") as HTMLTextAreaElement;
    expect(editor.value).toContain("q-0001");
  });

  it("still shows the recognised cards when nothing is exportable", () => {
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    const editor = screen.getByLabelText("Deck JSON — editable") as HTMLTextAreaElement;
    expect(editor.value).toContain("q-0002");
    expect(screen.getByText(/every card was excluded/i)).toBeTruthy();
  });

  it("names blocked cards by the id they carry in the draft", () => {
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    expect(screen.getByText("q-0002")).toBeTruthy();
  });

  it("refuses to download a draft the backend has not cleared", async () => {
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    const download = screen.getByRole("button", { name: /download deck-01\.json/i });
    expect((download as HTMLButtonElement).disabled).toBe(true);
    await waitFor(() => expect(checkDeck).toHaveBeenCalled());
    await screen.findByText(/mark exactly one correct option/i);
    expect((download as HTMLButtonElement).disabled).toBe(true);
  });

  it("allows the download once the backend clears it", async () => {
    checkDeck.mockResolvedValue({ ok: true, errors: [], deck: DECK, config: { decks: { "deck-01": {} } } });
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    const download = screen.getByRole("button", { name: /download deck-01\.json/i });
    await waitFor(() => expect((download as HTMLButtonElement).disabled).toBe(false));
  });

  it("offers config.json only after the backend clears the deck", async () => {
    checkDeck.mockResolvedValue({ ok: true, errors: [], deck: DECK, config: { topicKey: "clauses" } });
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    const config = screen.getByRole("button", { name: /download config\.json/i });
    await waitFor(() => expect((config as HTMLButtonElement).disabled).toBe(false));
  });

  it("lets a person take the questions away even when nothing is exportable", () => {
    // The worst case still has to produce a file: the draft carries each card's status in the
    // JSON, so the work can be finished in any editor rather than being trapped behind the gate.
    render(
      <ExportPanel
        exportInfo={exportInfo({ deck: null, blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    const draft = screen.getByRole("button", { name: /download draft json/i }) as HTMLButtonElement;
    expect(draft.disabled).toBe(false);
  });

  it("offers the blocked cards alongside a partial export rather than burying them", () => {
    render(
      <ExportPanel
        exportInfo={exportInfo({ blocked: BLOCKED, blockedCardIds: ["c-77"] })}
        deckTitle="clauses"
      />,
    );
    expect(screen.getByRole("radio", { name: /draft with the 1 excluded card/i })).toBeTruthy();
  });
});
