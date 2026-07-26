// DeckJsonViewer.tsx — lightweight JSON preview using a plain <pre>.
// The donor (razbiram-anki) uses CodeMirror here, but that dependency is not
// in this app's package.json.  The CSS class names are kept identical so the
// visual container stays consistent across the family.

export default function DeckJsonViewer({ value }: { value: string }) {
  return (
    <div className="rz-json-viewer">
      <pre
        style={{
          margin: 0,
          padding: "12px 14px",
          fontSize: 12,
          lineHeight: 1.6,
          overflowX: "auto",
          overflowY: "auto",
          maxHeight: 360,
          color: "var(--text)",
          background: "var(--surface)",
          whiteSpace: "pre",
          fontFamily: "ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace",
        }}
      >
        {value}
      </pre>
    </div>
  );
}
