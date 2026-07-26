// App.tsx — razbiram-screen-to-learn studio.
//
// Shell adapted from razbiram-anki/src/App.tsx: same NodeMark, same theme
// hook, same drop zone pattern, same panel structure.  The middle layer
// (browser-side Anki conversion) is replaced by a POST to /v1/process.
import { useCallback, useMemo, useRef, useState } from "react";
import { processFile } from "./api";
import type { ProcessResponse, ProcessExport } from "./types";
import { CardList } from "./CardList";
import { IssueList } from "./IssueList";
import DeckJsonViewer from "./DeckJsonViewer";

// ---------------------------------------------------------------------------
// Brand components (kept verbatim from the donor)
// ---------------------------------------------------------------------------

/** The razbiram node-mark — © razbiram.com, drawn in code (no image asset). */
function NodeMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" className="rz-node" aria-hidden="true">
      <line x1="17" y1="17" x2="6"  y2="7"  stroke="currentColor" strokeWidth="1.7" />
      <line x1="17" y1="17" x2="29" y2="9"  stroke="currentColor" strokeWidth="1.7" />
      <line x1="17" y1="17" x2="9"  y2="28" stroke="currentColor" strokeWidth="1.7" />
      <line x1="17" y1="17" x2="27" y2="27" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="6"  cy="7"  r="3"   fill="currentColor" />
      <circle cx="29" cy="9"  r="2.5" fill="currentColor" />
      <circle cx="9"  cy="28" r="2.5" fill="currentColor" />
      <circle cx="27" cy="27" r="2.5" fill="currentColor" />
      <circle cx="17" cy="17" r="5"   fill="currentColor" />
    </svg>
  );
}

function Wordmark() {
  return (
    <span className="rz-wordmark" style={{ fontSize: 24 }}>
      razb<span className="accent">i</span>ram
      <span className="sub">-screen-to-learn</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

type Theme = "light" | "dark";

function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(
    () =>
      (document.documentElement.getAttribute("data-theme") as Theme) ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );
  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      return next;
    });
  }, []);
  return [theme, toggle];
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function downloadJson(obj: unknown, filename: string): void {
  const json = JSON.stringify(obj, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Status machine
// ---------------------------------------------------------------------------

type Status =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "done"; result: ProcessResponse }
  | { phase: "error"; message: string };

// ---------------------------------------------------------------------------
// Export panel
// ---------------------------------------------------------------------------

function ExportPanel({ exportInfo, deckTitle }: { exportInfo: ProcessExport; deckTitle: string }) {
  const [showJson, setShowJson] = useState(false);
  const [copied, setCopied] = useState(false);

  const exportJson = useMemo(
    () => (exportInfo.deck ? JSON.stringify(exportInfo.deck, null, 2) : ""),
    [exportInfo.deck],
  );

  const onCopy = useCallback(() => {
    if (!exportJson) return;
    navigator.clipboard.writeText(exportJson).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  }, [exportJson]);

  const onDownload = useCallback(() => {
    if (!exportInfo.deck) return;
    downloadJson(exportInfo.deck, `${deckTitle || "export"}.json`);
  }, [exportInfo.deck, deckTitle]);

  return (
    <section style={{ marginTop: 20 }}>
      <h2 style={{ fontSize: 20, margin: "0 0 10px", letterSpacing: "-0.01em" }}>
        Export
      </h2>

      {exportInfo.deck === null ? (
        // All cards were blocked — no deck to export
        <div
          className="rz-card"
          style={{ borderColor: "var(--danger)", background: "var(--danger-soft)" }}
        >
          <div style={{ fontWeight: 700, color: "var(--danger)", marginBottom: 8 }}>
            Export blocked — every card was excluded
          </div>
          <div className="rz-muted" style={{ fontSize: 14, marginBottom: exportInfo.blocked.length > 0 ? 12 : 0 }}>
            Fix the blocking issues and re-process the file to get an exportable deck.
          </div>
          {exportInfo.blocked.length > 0 && (
            <ul style={{ margin: 0, padding: "0 0 0 18px", display: "grid", gap: 4 }}>
              {exportInfo.blocked.map((b) => (
                <li key={b.cardId} style={{ fontSize: 13, color: "var(--danger)" }}>
                  <code className="rz-faint">{b.cardId}</code>
                  {" — "}
                  {b.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        // Deck is exportable (may be partial if some cards were blocked)
        <div className="rz-card">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
            <span className="rz-chip">{exportInfo.deck.schemaId}</span>
            {typeof exportInfo.deck.meta.cardCount === "number" && (
              <span className="rz-chip">
                <span className="rz-numeral">{exportInfo.deck.meta.cardCount}</span>
                {" "}card{exportInfo.deck.meta.cardCount !== 1 ? "s" : ""}
              </span>
            )}
            {exportInfo.blockedCardIds.length > 0 && (
              <span
                className="rz-chip"
                style={{ color: "var(--warn)", borderColor: "var(--warn)" }}
              >
                {exportInfo.blockedCardIds.length} card{exportInfo.blockedCardIds.length !== 1 ? "s" : ""} excluded
              </span>
            )}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
            <button
              className="rz-btn rz-btn-primary"
              onClick={onDownload}
              style={{ minHeight: 44 }}
            >
              Download export JSON
            </button>
            <button
              className="rz-btn"
              onClick={() => setShowJson((v) => !v)}
              aria-expanded={showJson}
              style={{ minHeight: 44 }}
            >
              {showJson ? "Hide JSON" : "Preview JSON"}
            </button>
            {showJson && (
              <button className="rz-btn" onClick={onCopy} style={{ minHeight: 44 }}>
                {copied ? "Copied ✓" : "Copy"}
              </button>
            )}
          </div>

          {showJson && (
            <div style={{ marginTop: 14 }}>
              <DeckJsonViewer value={exportJson} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Unsupported section
// ---------------------------------------------------------------------------

function UnsupportedSection({ ids }: { ids: string[] }) {
  if (ids.length === 0) return null;
  return (
    <section style={{ marginTop: 20 }}>
      <h2 style={{ fontSize: 20, margin: "0 0 8px", letterSpacing: "-0.01em" }}>
        Unsupported question types{" "}
        <span className="rz-numeral">{ids.length}</span>
      </h2>
      <div
        className="rz-card"
        style={{ borderColor: "var(--warn)", background: "var(--warn-soft)" }}
      >
        <div className="rz-muted" style={{ fontSize: 14, marginBottom: 10 }}>
          These question IDs were recognised in the source but cannot be extracted yet.
          They do not appear in the card list above and were not included in the export.
        </div>
        <ul style={{ margin: 0, padding: "0 0 0 18px", display: "grid", gap: 4 }}>
          {ids.map((id) => (
            <li key={id} style={{ fontSize: 13 }}>
              <code className="rz-faint">{id}</code>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Result view
// ---------------------------------------------------------------------------

function Result({ result }: { result: ProcessResponse }) {
  const { captureIr, issues, unsupported } = result;
  const exportInfo = result.export;
  const { deck } = captureIr;
  const exportedCount = captureIr.cards.length - exportInfo.blockedCardIds.length;

  return (
    <div style={{ marginTop: 20 }}>
      {/* Deck summary card */}
      <div className="rz-card">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          {deck.level && <span className="rz-chip">{deck.level}</span>}
          {deck.difficulty && <span className="rz-chip">{deck.difficulty}</span>}
          {deck.tags.map((tag) => (
            <span key={tag} className="rz-chip">{tag}</span>
          ))}
        </div>
        <div style={{ fontWeight: 700, fontSize: 18, margin: "12px 0 4px" }}>
          {deck.title.en}
        </div>
        {deck.description.en && (
          <div className="rz-muted" style={{ fontSize: 15, marginBottom: 8 }}>
            {deck.description.en}
          </div>
        )}
        <div className="rz-muted" style={{ fontSize: 14 }}>
          <span className="rz-numeral">{captureIr.cards.length}</span> card
          {captureIr.cards.length !== 1 ? "s" : ""} extracted
          {exportInfo.blockedCardIds.length > 0 && (
            <>
              {" · "}
              <span className="rz-numeral" style={{ color: "var(--ok)" }}>{exportedCount}</span> exportable
              {" · "}
              <span className="rz-numeral" style={{ color: "var(--danger)" }}>
                {exportInfo.blockedCardIds.length}
              </span> blocked
            </>
          )}
          {unsupported.length > 0 && (
            <>
              {" · "}
              <span className="rz-numeral" style={{ color: "var(--warn)" }}>{unsupported.length}</span> unsupported
            </>
          )}
        </div>
      </div>

      <CardList cards={captureIr.cards} exportInfo={exportInfo} />
      <UnsupportedSection ids={unsupported} />
      <IssueList issues={issues} />
      <ExportPanel exportInfo={exportInfo} deckTitle={deck.title.en} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [isOver, setIsOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>({ phase: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = useCallback((f: File | undefined) => {
    if (!f) return;
    const name = f.name.toLowerCase();
    if (!name.endsWith(".html") && !name.endsWith(".txt")) {
      setFile(f);
      setStatus({
        phase: "error",
        message: "Please select an .html or .txt file.",
      });
      return;
    }
    setFile(f);
    setStatus({ phase: "uploading" });
    processFile(f)
      .then((result) => setStatus({ phase: "done", result }))
      .catch((err: unknown) =>
        setStatus({
          phase: "error",
          message: err instanceof Error ? err.message : "Upload failed.",
        }),
      );
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsOver(false);
      accept(e.dataTransfer.files[0]);
    },
    [accept],
  );

  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "18px 20px",
          maxWidth: 880,
          margin: "0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <NodeMark />
          <Wordmark />
        </div>
        <button
          className="rz-btn"
          onClick={toggleTheme}
          aria-label="Toggle colour scheme"
          style={{ minHeight: 44 }}
        >
          {theme === "dark" ? "☀ Light" : "☾ Dark"}
        </button>
      </header>

      <main style={{ maxWidth: 720, margin: "0 auto", padding: "8px 20px 64px" }}>
        <h1 style={{ fontSize: 30, lineHeight: 1.15, margin: "18px 0 8px", letterSpacing: "-0.01em" }}>
          Screen capture → review-ready learning cards
        </h1>
        <p className="rz-muted" style={{ fontSize: 18, margin: "0 0 24px", maxWidth: 560 }}>
          Drop a captured HTML or text file here. The backend extracts the
          questions, validates them, and gives you a structured deck ready for
          human review — before anything is exported.
        </p>

        {/* Drop zone — keyboard-operable via role="button" + tabIndex + onKeyDown */}
        <div
          className={`rz-dropzone${isOver ? " is-over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsOver(true);
          }}
          onDragLeave={() => setIsOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          role="button"
          tabIndex={0}
          aria-label="Drop an .html or .txt file here, or press Enter to browse"
        >
          <input
            ref={inputRef}
            type="file"
            accept=".html,.txt,text/html,text/plain"
            style={{ display: "none" }}
            onChange={(e) => accept(e.target.files?.[0])}
          />
          <div style={{ fontSize: 40, marginBottom: 8 }}>📄</div>
          {file ? (
            <>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{file.name}</div>
              <div className="rz-faint" style={{ marginTop: 4 }}>{humanSize(file.size)}</div>
            </>
          ) : (
            <>
              <div style={{ fontWeight: 700, fontSize: 18 }}>Drop your capture file here</div>
              <div className="rz-muted" style={{ marginTop: 4 }}>or click to browse</div>
              <div className="rz-faint" style={{ marginTop: 6, fontSize: 13 }}>
                accepts .html and .txt
              </div>
            </>
          )}
        </div>

        {status.phase === "uploading" && (
          <div className="rz-card rz-muted" style={{ marginTop: 20 }}>
            Processing — sending to local backend …
          </div>
        )}

        {status.phase === "error" && (
          <div className="rz-card" style={{ marginTop: 20, borderColor: "var(--primary)" }}>
            <strong>Something went wrong.</strong>
            <div className="rz-muted" style={{ marginTop: 6 }}>{status.message}</div>
          </div>
        )}

        {status.phase === "done" && <Result result={status.result} />}
      </main>

      <footer
        className="rz-faint"
        style={{ maxWidth: 720, margin: "0 auto", padding: "0 20px 40px", fontSize: 13 }}
      >
        Part of the razbiram ecosystem · razbiram-screen-to-learn · visual identity © razbiram.com
      </footer>
    </div>
  );
}
