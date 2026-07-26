// DeckJsonViewer.tsx — the deck JSON, editable in place.
//
// Read-only when no `onChange` is given, a plain <textarea> when there is one.  The donor
// (razbiram-anki) reaches for CodeMirror here; that dependency is not in this app's package.json
// and a textarea is enough for the one job this has — letting a person correct a card the
// extractor could not resolve before they download it.  The CSS class names are kept identical so
// the visual container stays consistent across the family.

const BOX = {
  margin: 0,
  padding: "12px 14px",
  fontSize: 12,
  lineHeight: 1.6,
  color: "var(--text)",
  background: "var(--surface)",
  fontFamily: "ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace",
} as const;

export default function DeckJsonViewer({
  value,
  onChange,
  invalid = false,
}: {
  value: string;
  onChange?: (next: string) => void;
  /** True when `value` does not parse — the border says so without blocking the edit. */
  invalid?: boolean;
}) {
  if (!onChange) {
    return (
      <div className="rz-json-viewer">
        <pre style={{ ...BOX, overflowX: "auto", overflowY: "auto", maxHeight: 360, whiteSpace: "pre" }}>
          {value}
        </pre>
      </div>
    );
  }

  return (
    <div className="rz-json-viewer">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        aria-label="Deck JSON — editable"
        aria-invalid={invalid}
        style={{
          ...BOX,
          display: "block",
          width: "100%",
          height: 360,
          resize: "vertical",
          border: `1px solid ${invalid ? "var(--danger, #c0392b)" : "transparent"}`,
          borderRadius: 8,
          outlineOffset: 2,
          whiteSpace: "pre",
          overflowWrap: "normal",
          overflowX: "auto",
        }}
      />
    </div>
  );
}
