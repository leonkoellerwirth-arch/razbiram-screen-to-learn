// IssueList.tsx — renders the validation report from /v1/process.
// Blocking issues are shown in danger styling and listed first.
// Non-blocking warnings are styled in amber.
// A prominent success message appears when there are no issues at all.
import type { Issue } from "./types";

function IssueRow({ issue }: { issue: Issue }) {
  const blocking = issue.blocking;
  const color = blocking ? "var(--danger)" : "var(--warn)";
  const bg = blocking ? "var(--danger-soft)" : "var(--warn-soft)";

  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: "var(--r-sm)",
        border: `1px solid ${color}`,
        background: bg,
        display: "grid",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: "0.04em",
            color,
            padding: "1px 7px",
            borderRadius: 999,
            border: `1px solid ${color}`,
          }}
        >
          {blocking ? "BLOCKING" : "WARNING"}
        </span>
        <code style={{ fontSize: 12, color: "var(--faint)" }}>{issue.code}</code>
        {issue.cardId && (
          <span className="rz-faint" style={{ fontSize: 12 }}>
            {issue.cardId}
          </span>
        )}
      </div>
      <div className="rz-muted" style={{ fontSize: 14 }}>
        {issue.message}
      </div>
    </div>
  );
}

export function IssueList({ issues }: { issues: Issue[] }) {
  const blocking = issues.filter((i) => i.blocking);
  const warnings = issues.filter((i) => !i.blocking);

  return (
    <section style={{ marginTop: 20 }}>
      <h2 style={{ fontSize: 20, margin: "0 0 10px", letterSpacing: "-0.01em" }}>
        Validation
      </h2>

      {issues.length === 0 && (
        <div
          className="rz-card"
          style={{
            borderColor: "var(--ok)",
            background: "var(--ok-soft)",
            color: "var(--ok)",
            fontWeight: 700,
          }}
        >
          ✓ No issues found — all cards passed validation.
        </div>
      )}

      {blocking.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--danger)",
              marginBottom: 8,
            }}
          >
            {blocking.length} blocking issue{blocking.length !== 1 ? "s" : ""}{" "}
            — these prevent export of affected cards
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {blocking.map((issue, idx) => (
              <IssueRow key={`block-${idx}`} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--warn)",
              marginBottom: 8,
            }}
          >
            {warnings.length} warning{warnings.length !== 1 ? "s" : ""}
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {warnings.map((issue, idx) => (
              <IssueRow key={`warn-${idx}`} issue={issue} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
