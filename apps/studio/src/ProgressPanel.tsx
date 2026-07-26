// ProgressPanel.tsx — what the backend is doing, while it is doing it.
//
// The rule this component exists to keep: never show a proportion nobody measured. Reading a
// large screenshot takes about a minute here and no honest percentage of it exists, so the bar is
// determinate only while a real count is in hand (upload bytes, OCR attempt n of 3, card n of m)
// and indeterminate otherwise — with elapsed time, which is always true.

import { useEffect, useState } from "react";
import type { StageEvent } from "./api";

const LABELS: Record<string, string> = {
  receiving: "Receiving the file",
  reading: "Reading the image",
  segmenting: "Finding the questions",
  validating: "Checking the cards",
  exporting: "Building the deck",
};

function useElapsed(since: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(id);
  }, []);
  return Math.max(0, Math.round((now - since) / 1000));
}

export default function ProgressPanel({
  since,
  uploaded,
  stage,
}: {
  /** Epoch ms when this run started. */
  since: number;
  /** Fraction of the file sent, 0..1, or null once the upload finished. */
  uploaded: number | null;
  /** The most recent stage the backend reported, or null while nothing has arrived yet. */
  stage: StageEvent | null;
}) {
  const elapsed = useElapsed(since);

  const uploading = uploaded !== null && uploaded < 1 && stage === null;
  const counted = stage?.total != null && stage.total > 0 && stage.index != null;
  const fraction = uploading ? uploaded : counted ? stage!.index! / stage!.total! : null;

  const heading = uploading
    ? "Sending the file"
    : stage
      ? (LABELS[stage.stage] ?? "Working")
      : "Starting";

  return (
    <div
      className="rz-card"
      style={{ marginTop: 20, padding: 18 }}
      role="status"
      aria-live="polite"
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
        <strong>{heading}</strong>
        <span className="rz-faint" style={{ fontVariantNumeric: "tabular-nums" }}>
          {elapsed}s
        </span>
      </div>

      <div
        style={{ height: 8, borderRadius: 999, background: "var(--surface)", overflow: "hidden" }}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        {...(fraction === null
          ? { "aria-valuetext": "in progress, remaining time unknown" }
          : { "aria-valuenow": Math.round(fraction * 100) })}
      >
        <div
          style={
            fraction === null
              ? {
                  // No measurement exists, so the bar paces rather than fills — it must not imply
                  // a position it does not know.
                  height: "100%",
                  width: "35%",
                  borderRadius: 999,
                  background: "var(--primary)",
                  animation: "rz-indeterminate 1.4s ease-in-out infinite",
                }
              : {
                  height: "100%",
                  width: `${Math.min(100, Math.round(fraction * 100))}%`,
                  borderRadius: 999,
                  background: "var(--primary)",
                  transition: "width 180ms linear",
                }
          }
        />
      </div>

      <p className="rz-muted" style={{ margin: "10px 2px 0", fontSize: 13 }}>
        {uploading
          ? `${Math.round((uploaded ?? 0) * 100)}% sent`
          : (stage?.detail ?? "Waiting for the backend…")}
      </p>

      {stage?.stage === "reading" && (
        <p className="rz-faint" style={{ margin: "6px 2px 0", fontSize: 12 }}>
          A full-page screenshot can take a minute. Each attempt reads the whole image with a
          different page layout assumption, and the first one that finds questions wins — so
          finishing early is normal.
        </p>
      )}
    </div>
  );
}
