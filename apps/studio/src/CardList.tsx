// CardList.tsx — per-card review panels.
//
// Every card is shown regardless of blocked / exportable status.  Hiding a
// blocked card (or making it look exportable) would defeat the human-review
// purpose of this tool.
import type { Card, Option, ProcessExport } from "./types";

const FAMILY_LABELS: Record<string, string> = {
  "single-choice": "Single choice",
  "multiple-select": "Multiple select",
  "true-false": "True / False",
  flashcard: "Flashcard",
};

// --- sub-renderers ---------------------------------------------------------

function OptionRow({ opt }: { opt: Option }) {
  return (
    <li
      style={{
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
        padding: "7px 10px",
        borderRadius: "var(--r-sm)",
        border: "1px solid var(--hairline)",
        background: opt.isCorrect ? "var(--ok-soft)" : "var(--surface-2)",
      }}
    >
      <span
        style={{
          fontWeight: 800,
          flexShrink: 0,
          color: opt.isCorrect ? "var(--ok)" : "var(--faint)",
          minWidth: 16,
        }}
        aria-label={opt.isCorrect ? "correct" : "incorrect"}
      >
        {opt.isCorrect ? "✓" : "✗"}
      </span>
      <span style={{ color: opt.isCorrect ? "var(--text)" : "var(--muted)" }}>
        {opt.text}
      </span>
    </li>
  );
}

function TrueFalseBody({ card }: { card: Card }) {
  const label =
    card.answer === true
      ? (card.labels?.true ?? "True")
      : (card.labels?.false ?? "False");

  return (
    <div style={{ marginTop: 8 }}>
      {card.statement && (
        <div
          style={{
            padding: "7px 10px",
            borderRadius: "var(--r-sm)",
            border: "1px solid var(--hairline)",
            background: "var(--surface-2)",
            marginBottom: 8,
          }}
        >
          <div className="rz-faint" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", marginBottom: 2 }}>
            STATEMENT
          </div>
          <div>{card.statement.value.en}</div>
        </div>
      )}
      <span
        className="rz-chip"
        style={{
          background: "var(--ok-soft)",
          color: "var(--ok)",
          borderColor: "transparent",
        }}
      >
        Answer: {label}
      </span>
    </div>
  );
}

function FlashcardBody({ card }: { card: Card }) {
  return (
    <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
      {card.front && (
        <div
          style={{
            padding: "7px 10px",
            borderRadius: "var(--r-sm)",
            border: "1px solid var(--hairline)",
            background: "var(--surface-2)",
          }}
        >
          <div className="rz-faint" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", marginBottom: 2 }}>
            FRONT
          </div>
          <div>{card.front.value.en}</div>
        </div>
      )}
      {card.back && (
        <div
          style={{
            padding: "7px 10px",
            borderRadius: "var(--r-sm)",
            border: "1px solid var(--hairline)",
            background: "var(--surface-2)",
          }}
        >
          <div className="rz-faint" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", marginBottom: 2 }}>
            BACK
          </div>
          <div>{card.back.value.en}</div>
        </div>
      )}
    </div>
  );
}

// --- main card panel -------------------------------------------------------

function CardPanel({
  card,
  blocked,
  blockedReason,
}: {
  card: Card;
  blocked: boolean;
  blockedReason: string | undefined;
}) {
  return (
    <div
      className="rz-card"
      style={{
        marginBottom: 12,
        borderWidth: blocked ? 2 : 1,
        borderColor: blocked ? "var(--danger)" : "var(--hairline)",
      }}
    >
      {/* header row */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <span className="rz-chip">{FAMILY_LABELS[card.family] ?? card.family}</span>
        {blocked && (
          <span
            className="rz-chip"
            style={{
              background: "var(--danger-soft)",
              color: "var(--danger)",
              borderColor: "var(--danger)",
              fontWeight: 800,
            }}
          >
            BLOCKED — not exported
          </span>
        )}
        <span className="rz-chip" style={{ marginLeft: "auto" }}>
          {card.answerEvidenceTier}
        </span>
      </div>

      {/* prompt */}
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{card.prompt.value.en}</div>

      {/* family-specific body */}
      {(card.family === "single-choice" || card.family === "multiple-select") &&
        card.options &&
        card.options.length > 0 && (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 6 }}>
            {card.options.map((opt) => (
              <OptionRow key={opt.optionId} opt={opt} />
            ))}
          </ul>
        )}

      {card.family === "true-false" && <TrueFalseBody card={card} />}
      {card.family === "flashcard" && <FlashcardBody card={card} />}

      {/* blocked reason — must always be visible when blocked */}
      {blocked && blockedReason && (
        <div
          style={{
            marginTop: 10,
            padding: "8px 10px",
            borderRadius: "var(--r-sm)",
            background: "var(--danger-soft)",
            color: "var(--danger)",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Why blocked: {blockedReason}
        </div>
      )}

      {/* card id — for traceability */}
      <div className="rz-faint" style={{ marginTop: 10, fontSize: 11 }}>
        {card.cardId}
      </div>
    </div>
  );
}

// --- list ------------------------------------------------------------------

export function CardList({
  cards,
  exportInfo,
}: {
  cards: Card[];
  exportInfo: ProcessExport;
}) {
  const blockedSet = new Set(exportInfo.blockedCardIds);
  const reasonMap = new Map(exportInfo.blocked.map((b) => [b.cardId, b.reason]));

  const exported = cards.filter((c) => !blockedSet.has(c.cardId));
  const blocked = cards.filter((c) => blockedSet.has(c.cardId));

  return (
    <section style={{ marginTop: 20 }}>
      <h2 style={{ fontSize: 20, margin: "0 0 4px", letterSpacing: "-0.01em" }}>
        Cards{" "}
        <span className="rz-numeral">{cards.length}</span>
      </h2>

      {cards.length === 0 && (
        <div className="rz-card rz-muted" style={{ marginTop: 8 }}>
          No cards were extracted from this file.
        </div>
      )}

      {exported.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {exported.length < cards.length && (
            <div className="rz-faint" style={{ fontSize: 13, marginBottom: 8 }}>
              {exported.length} card{exported.length !== 1 ? "s" : ""} included in export
            </div>
          )}
          {exported.map((card) => (
            <CardPanel
              key={card.cardId}
              card={card}
              blocked={false}
              blockedReason={undefined}
            />
          ))}
        </div>
      )}

      {blocked.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--danger)",
              marginBottom: 8,
            }}
          >
            {blocked.length} blocked card{blocked.length !== 1 ? "s" : ""} — present in input but excluded from export
          </div>
          {blocked.map((card) => (
            <CardPanel
              key={card.cardId}
              card={card}
              blocked={true}
              blockedReason={reasonMap.get(card.cardId)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
