// App.tsx — razbiram-screen-to-learn studio.
//
// Shell adapted from razbiram-anki/src/App.tsx: same NodeMark, same theme
// hook, same drop zone pattern, same panel structure.  The middle layer
// (browser-side Anki conversion) is replaced by a POST to /v1/process.
import { useCallback, useRef, useState } from "react";
import { importQuizletUrl, processFileStreaming } from "./api";
import type { StageEvent } from "./api";
import type { ProcessResponse } from "./types";
import { CardList } from "./CardList";
import { IssueList } from "./IssueList";
import ExportPanel from "./ExportPanel";
import ProgressPanel from "./ProgressPanel";

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

function localized(value: Record<string, string>): string {
  return value.en ?? Object.values(value)[0] ?? "";
}


/**
 * What the studio takes in. Images go through OCR on the server; .html/.txt are read directly.
 * Mirrors ALLOWED_SUFFIXES in studio/server.py — the server rejects anything else regardless.
 */
const ACCEPTED_SUFFIXES = [
  ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif",
  ".html", ".htm", ".txt", ".md",
] as const;

// ---------------------------------------------------------------------------
// Status machine
// ---------------------------------------------------------------------------

type Status =
  | { phase: "idle" }
  | { phase: "working"; since: number; uploaded: number | null; stage: StageEvent | null }
  | { phase: "done"; result: ProcessResponse }
  | { phase: "error"; message: string };

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
          {localized(deck.title)}
        </div>
        {localized(deck.description) && (
          <div className="rz-muted" style={{ fontSize: 15, marginBottom: 8 }}>
            {localized(deck.description)}
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
      <ExportPanel exportInfo={exportInfo} deckTitle={localized(deck.title)} />
    </div>
  );
}

function QuizletImport({
  onStart,
  onDone,
  onError,
}: {
  onStart: () => void;
  onDone: (result: ProcessResponse) => void;
  onError: (message: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [termLocale, setTermLocale] = useState("en");
  const [definitionLocale, setDefinitionLocale] = useState("en");

  const submit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      onStart();
      importQuizletUrl(url.trim(), termLocale.trim() || "en", definitionLocale.trim() || "en")
        .then(onDone)
        .catch((err: unknown) =>
          onError(err instanceof Error ? err.message : "Quizlet import failed."),
        );
    },
    [definitionLocale, onDone, onError, onStart, termLocale, url],
  );

  return (
    <form className="rz-card" onSubmit={submit} style={{ display: "grid", gap: 12 }}>
      <label style={{ display: "grid", gap: 6 }}>
        <span style={{ fontWeight: 700 }}>Quizlet flashcards URL</span>
        <input
          className="rz-input"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://quizlet.com/.../flash-cards/"
          required
        />
      </label>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontWeight: 700 }}>Term language</span>
          <input
            className="rz-input"
            value={termLocale}
            onChange={(event) => setTermLocale(event.target.value)}
            maxLength={12}
          />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontWeight: 700 }}>Definition language</span>
          <input
            className="rz-input"
            value={definitionLocale}
            onChange={(event) => setDefinitionLocale(event.target.value)}
            maxLength={12}
          />
        </label>
      </div>

      <p className="rz-muted" style={{ margin: 0, fontSize: 14 }}>
        Uses Scrapling in a bounded browser session for this one URL. If Quizlet blocks the page,
        the import stops instead of trying to bypass the challenge.
      </p>

      <button className="rz-btn rz-btn-primary" type="submit" style={{ minHeight: 44 }}>
        Import from Quizlet
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [tab, setTab] = useState<"file" | "quizlet">("file");
  const [isOver, setIsOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>({ phase: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = useCallback((f: File | undefined) => {
    if (!f) return;
    const name = f.name.toLowerCase();
    if (!ACCEPTED_SUFFIXES.some((suffix) => name.endsWith(suffix))) {
      setFile(f);
      setStatus({
        phase: "error",
        message: `Please select an image, or an .html or .txt file. Accepted: ${ACCEPTED_SUFFIXES.join(", ")}`,
      });
      return;
    }
    setFile(f);
    setStatus({ phase: "working", since: Date.now(), uploaded: 0, stage: null });
    processFileStreaming(f, {
      onUpload: (fraction) =>
        setStatus((s) => (s.phase === "working" ? { ...s, uploaded: fraction } : s)),
      onStage: (stage) =>
        // The first stage means the bytes are in; from here the backend owns the narration.
        setStatus((s) => (s.phase === "working" ? { ...s, uploaded: null, stage } : s)),
    })
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
          Drop a screenshot, a photo of a page, or a captured HTML or text file.
          The questions and their answer key are read from the material — nothing
          is invented — and you get a structured deck to review, edit and download.
        </p>

        <div role="tablist" aria-label="Import source" style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          <button
            className={`rz-btn${tab === "file" ? " rz-btn-primary" : ""}`}
            role="tab"
            aria-selected={tab === "file"}
            onClick={() => setTab("file")}
            style={{ minHeight: 44 }}
          >
            File / screenshot
          </button>
          <button
            className={`rz-btn${tab === "quizlet" ? " rz-btn-primary" : ""}`}
            role="tab"
            aria-selected={tab === "quizlet"}
            onClick={() => setTab("quizlet")}
            style={{ minHeight: 44 }}
          >
            Quizlet URL
          </button>
        </div>

        {/* Drop zone — keyboard-operable via role="button" + tabIndex + onKeyDown */}
        {tab === "file" ? (
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
            aria-label="Drop a screenshot, photo, or an .html or .txt file here, or press Enter to browse"
          >
            <input
              ref={inputRef}
              type="file"
              accept={`image/*,${ACCEPTED_SUFFIXES.join(",")},text/html,text/plain`}
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
                <div style={{ fontWeight: 700, fontSize: 18 }}>Drop a screenshot or photo here</div>
                <div className="rz-muted" style={{ marginTop: 4 }}>or click to browse</div>
                <div className="rz-faint" style={{ marginTop: 6, fontSize: 13 }}>
                  images (read on this machine), .html, .txt
                </div>
              </>
            )}
          </div>
        ) : (
          <QuizletImport
            onStart={() =>
              setStatus({
                phase: "working",
                since: Date.now(),
                uploaded: null,
                stage: { stage: "quizlet", detail: "Capturing Quizlet with Scrapling" },
              })
            }
            onDone={(result) => setStatus({ phase: "done", result })}
            onError={(message) => setStatus({ phase: "error", message })}
          />
        )}

        {status.phase === "working" && (
          <ProgressPanel since={status.since} uploaded={status.uploaded} stage={status.stage} />
        )}

        {status.phase === "error" && (
          <div className="rz-card" style={{ marginTop: 20, borderColor: "var(--danger)" }}>
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
