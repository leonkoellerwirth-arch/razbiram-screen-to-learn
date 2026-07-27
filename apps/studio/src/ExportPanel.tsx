// ExportPanel.tsx — the deck JSON, always visible, and the gate that says when it may leave.
//
// The panel used to hide the editor whenever the export was blocked, which is exactly the moment a
// person most needs to see what was recognised: "0 exportable · 2 blocked" with no JSON on screen
// says nothing about what is wrong or where. So the editor is always here, seeded either with the
// export the pipeline produced or with the draft that includes the blocked cards.
//
// Nothing here decides whether a deck is exportable. That answer comes from POST /v1/deck/check,
// which runs the same rules as the export path — the browser only reports it and disables Download.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { checkDeck } from "./api";
import type { DeckCheck } from "./api";
import type { ProcessExport } from "./types";
import DeckJsonViewer from "./DeckJsonViewer";

/** Which JSON the editor holds. */
type Seed = "export" | "draft";

function downloadText(json: string, filename: string): void {
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function BlockedList({ blocked }: { blocked: ProcessExport["blocked"] }) {
  if (blocked.length === 0) return null;
  return (
    <ul style={{ margin: "10px 0 0", padding: "0 0 0 18px", display: "grid", gap: 4 }}>
      {blocked.map((b) => (
        <li key={b.cardId} style={{ fontSize: 13, color: "var(--danger)" }}>
          <code className="rz-faint">{b.draftCardId ?? b.cardId}</code>
          {" — "}
          {b.reason}
        </li>
      ))}
    </ul>
  );
}

export default function ExportPanel({
  exportInfo,
  deckTitle,
}: {
  exportInfo: ProcessExport;
  deckTitle: string;
}) {
  const { deck, draft, blocked, capabilities } = exportInfo;

  // The export is what may leave as it stands; the draft is what a person can still fix. Start on
  // whichever actually exists — when nothing exported, the draft is the only thing worth showing.
  const [seed, setSeed] = useState<Seed>(deck ? "export" : "draft");
  const [showJson, setShowJson] = useState(true);
  const [copied, setCopied] = useState(false);

  const source = seed === "export" ? deck : draft;
  const pristine = useMemo(() => (source ? `${JSON.stringify(source, null, 2)}\n` : ""), [source]);

  // The edited buffer. Copy and Download must read THIS, never the pristine extraction.
  const [text, setText] = useState(pristine);
  useEffect(() => setText(pristine), [pristine]);

  const parsed = useMemo<{ value: unknown } | null>(() => {
    if (!text.trim()) return null;
    try {
      return { value: JSON.parse(text) as unknown };
    } catch {
      return null;
    }
  }, [text]);

  const [check, setCheck] = useState<DeckCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const requestId = useRef(0);

  // Judged server-side, debounced: typing inside a string literal would otherwise fire a request
  // per keystroke, and every intermediate state of an edit is invalid anyway.
  useEffect(() => {
    if (!parsed) {
      setCheck(null);
      setChecking(false);
      return;
    }
    const ticket = ++requestId.current;
    setChecking(true);
    const timer = window.setTimeout(() => {
      checkDeck(parsed.value, capabilities)
        .then((result) => {
          if (ticket !== requestId.current) return; // a newer edit already superseded this answer
          setCheck(result);
          setChecking(false);
        })
        .catch(() => {
          if (ticket !== requestId.current) return;
          // The gate is unreachable, so it cannot say yes. An untouched export already passed it
          // on the way here; anything else stays closed rather than guessing.
          setCheck(null);
          setChecking(false);
        });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [parsed, capabilities]);

  const untouchedExport = seed === "export" && deck !== null && text === pristine;
  const downloadable = parsed !== null && (check?.ok === true || (check === null && !checking && untouchedExport));

  const onCopy = useCallback(() => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  }, [text]);

  const onDownload = useCallback(() => {
    if (!downloadable) return;
    // The backend hands back the deck to save — same content, working notes stripped — so a
    // cleared deck never ships a card still labelled "needs-answer". Falling back to the editor
    // text covers the untouched-export case, which never had those notes to begin with.
    const payload = check?.deck != null ? `${JSON.stringify(check.deck, null, 2)}\n` : text;
    downloadText(payload, `${deckTitle || "export"}.json`);
  }, [downloadable, check, text, deckTitle]);

  // Always available, even when nothing is exportable. A person who cannot finish the answers here
  // must still be able to take the questions away and finish them elsewhere: the draft carries its
  // own status per card, so the file says what is missing without this screen.
  const onDownloadDraft = useCallback(() => {
    downloadText(text, `${deckTitle || "capture"}.draft.json`);
  }, [text, deckTitle]);

  if (!deck && !draft) return null;

  const cardCount = (source as { meta?: { cardCount?: number } } | null)?.meta?.cardCount;

  return (
    <section style={{ marginTop: 20 }}>
      <h2 style={{ fontSize: 20, margin: "0 0 10px", letterSpacing: "-0.01em" }}>Export</h2>

      <div
        className="rz-card"
        style={deck ? undefined : { borderColor: "var(--danger)", background: "var(--danger-soft)" }}
      >
        {!deck && (
          <>
            <div style={{ fontWeight: 700, color: "var(--danger)", marginBottom: 8 }}>
              Nothing is exportable yet — every card was excluded
            </div>
            <div className="rz-muted" style={{ fontSize: 14 }}>
              What was recognised is below. Mark the answer the material shows, then download —
              or re-process the file once the source issue is fixed.
            </div>
          </>
        )}

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginTop: deck ? 0 : 12 }}>
          <span className="rz-chip">{source?.schemaId}</span>
          {typeof cardCount === "number" && (
            <span className="rz-chip">
              <span className="rz-numeral">{cardCount}</span> card{cardCount !== 1 ? "s" : ""}
            </span>
          )}
          {deck && blocked.length > 0 && (
            <span className="rz-chip" style={{ color: "var(--warn)", borderColor: "var(--warn)" }}>
              {blocked.length} card{blocked.length !== 1 ? "s" : ""} excluded
            </span>
          )}
        </div>

        {/* Both exist and they differ — the person chooses what the editor holds. */}
        {deck && draft && blocked.length > 0 && (
          <div
            role="radiogroup"
            aria-label="Which JSON to show"
            style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}
          >
            <button
              className={`rz-btn${seed === "export" ? " rz-btn-primary" : ""}`}
              role="radio"
              aria-checked={seed === "export"}
              onClick={() => setSeed("export")}
              style={{ minHeight: 44 }}
            >
              Exportable deck
            </button>
            <button
              className={`rz-btn${seed === "draft" ? " rz-btn-primary" : ""}`}
              role="radio"
              aria-checked={seed === "draft"}
              onClick={() => setSeed("draft")}
              style={{ minHeight: 44 }}
            >
              Draft with the {blocked.length} excluded card{blocked.length !== 1 ? "s" : ""}
            </button>
          </div>
        )}

        <BlockedList blocked={seed === "draft" || !deck ? blocked : []} />

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
          <button
            className="rz-btn rz-btn-primary"
            onClick={onDownload}
            disabled={!downloadable}
            title={downloadable ? undefined : "This deck does not pass the target's rules yet."}
            style={{ minHeight: 44 }}
          >
            Download export JSON
          </button>
          <button className="rz-btn" onClick={onDownloadDraft} style={{ minHeight: 44 }}>
            Download draft JSON
          </button>
          <button
            className="rz-btn"
            onClick={() => setShowJson((v) => !v)}
            aria-expanded={showJson}
            style={{ minHeight: 44 }}
          >
            {showJson ? "Hide JSON" : "Show JSON"}
          </button>
          {showJson && (
            <button className="rz-btn" onClick={onCopy} style={{ minHeight: 44 }}>
              {copied ? "Copied ✓" : "Copy"}
            </button>
          )}
        </div>

        {showJson && (
          <div style={{ marginTop: 14 }}>
            <DeckJsonViewer value={text} onChange={setText} invalid={parsed === null} />
            {parsed === null ? (
              <p style={{ margin: "8px 2px 0", fontSize: 12, color: "var(--danger)" }}>
                This is not valid JSON yet, so Download is disabled.
              </p>
            ) : check && !check.ok ? (
              <div style={{ marginTop: 8 }}>
                <p style={{ margin: "0 2px 4px", fontSize: 12, color: "var(--warn)" }}>
                  Fix these before the deck can be exported:
                </p>
                <ul style={{ margin: 0, padding: "0 0 0 18px", display: "grid", gap: 3 }}>
                  {check.errors.map((error) => (
                    <li key={error} style={{ fontSize: 12, color: "var(--warn)" }}>
                      {error}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p style={{ margin: "8px 2px 0", fontSize: 12, opacity: 0.75 }}>
                {checking
                  ? "Checking against the target's rules…"
                  : "Edit freely — Copy and Download take what you see here."}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
