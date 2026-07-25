# Input channels

## One pipeline, several evidence qualities

The standalone app accepts screenshots, PDFs, pasted/uploaded text, extension bundles, and a
controlled-browser fallback. These inputs differ in structure, not in downstream rules.

```text
input adapter → ingest-envelope.v1 → artifact store → extraction → Capture IR → review → export
```

An adapter may improve detection confidence, but it may never lower the answer-evidence
requirement.

| Channel | Structural evidence | Visual evidence | Typical review |
|---|---:|---:|---|
| Chrome/Firefox extension | high | visible viewport/region | low to medium |
| Controlled browser | high | viewport/region | low to medium |
| Text or Markdown | medium | none | medium |
| Digital PDF | medium | rendered page | medium |
| Scanned PDF | low | rendered page | high |
| Screenshot/image | low | image only | high |

## Standalone drop studio

The home screen supports drag-and-drop, file selection, and paste. Before extraction it shows:

- detected input kind, count, pages, dimensions, and size;
- local/cloud processing choice and estimated cost where relevant;
- content-retention setting;
- page/region selection;
- an explicit acknowledgement for material the user is allowed to process.

Each import creates one job and immutable source artifacts. Edits happen in Capture IR, never by
overwriting the original evidence.

## Screenshot and image input

Supported first-release formats should be PNG, JPEG, and WebP. HEIC can be added only with a
well-tested local decoder.

Preprocessing is deterministic:

1. validate signature and media type;
2. enforce byte, pixel, and decompression limits;
3. normalize orientation and color space;
4. retain the original hash;
5. allow crop, rotate, split, and ordering adjustments;
6. run local OCR first, then optional vision with explicit consent;
7. preserve bounding boxes and field-level provenance.

Multiple screenshots can represent consecutive questions or one scrolled question. The UI asks
the user to choose or confirms an automatic geometry-based join. Filename order alone does not
prove that images belong together.

## PDF input

PDF handling is page-selective and local-first:

1. parse the text layer and document outline;
2. render selected pages at bounded resolution;
3. correlate extracted text with page coordinates;
4. apply OCR only to pages or regions without a useful text layer;
5. detect recurring headers/footers separately from question content;
6. emit page-number and bounding-box provenance for every field.

Password-protected files require the user to unlock them locally. The tool does not bypass
passwords, DRM, print restrictions, or access controls. Active content, embedded scripts,
attachments, and external links are not executed. Page count, file size, pixel count, and
processing time have explicit limits.

Correct-answer keys may be on later pages. The importer can propose links using question numbers
and text fingerprints, but export stays blocked until the evidence is unambiguous or reviewed.

## Text input

The studio accepts pasted text and bounded `.txt`/`.md` files. Optional HTML is parsed only after
sanitization and is treated as content, never executed markup.

The parser recognizes common structures:

- numbered questions;
- lettered or bulleted options;
- checkboxes/radio-like markers;
- `True/False`, `Richtig/Falsch`, and configured locale pairs;
- answer-key sections;
- front/back separators for flashcards;
- tabular pairs for matching.

Text such as “What is X? A… B… C…” does not prove a correct option. A separate answer-key marker
or a reviewer confirmation is required.

## Extension bundle input

`.razcapture` is a portable evidence handoff, not a finished deck. Import performs:

- archive path and symlink safety checks;
- manifest schema and protocol compatibility checks;
- declared/actual size and hash checks;
- artifact media validation;
- semantic snapshot sanitization;
- duplicate capture detection;
- source-origin minimization before persistence.

The original extension bundle remains immutable until the retention policy deletes it.

The extension popup may expose `Open drop studio` for screenshots, PDFs, and text. This is an
acquisition and navigation shortcut; document processing still follows the standalone adapter
and review path. Capture Lite alone creates evidence, while the studio creates the final reviewed
Razbiram JSON.

## Controlled-browser fallback

A headed Playwright browser remains useful when:

- extension installation is not allowed;
- deterministic test fixtures or CI are required;
- the learner wants a clean, isolated browser profile;
- a platform behaves differently in the normal browser.

It is not the only or mandatory intake path. It writes the same extension-independent capture
manifest and follows the same explicit start/pause/stop rules.

## Ingest envelope

Every adapter maps its source into a small immutable envelope before extraction:

```json
{
  "schemaVersion": "ingest-envelope.v1",
  "ingestId": "ing_01J...",
  "createdAt": "2026-07-25T12:00:00Z",
  "sourceKind": "image-upload",
  "artifacts": [
    {
      "artifactId": "art_sha256-prefix",
      "role": "source-image",
      "mediaType": "image/png",
      "sha256": "64-lowercase-hex",
      "bytes": 182400
    }
  ],
  "sourceContext": {
    "displayName": "biophysics-question-01.png",
    "locale": "en"
  },
  "capabilities": {
    "semanticSnapshot": false,
    "geometry": true,
    "answerRevealSequence": false
  }
}
```

Allowed `sourceKind` values:

- `browser-extension`;
- `controlled-browser`;
- `extension-bundle`;
- `image-upload`;
- `pdf-upload`;
- `text-input`;
- `synthetic-fixture`.

Paths, URLs with queries, cookies, and credentials are not part of the portable envelope.

## Unified review behavior

The review UI always shows:

- the original evidence appropriate to the channel;
- extracted question, options, media, and answer key;
- whether each field is deterministic, model-extracted, or reviewer-entered;
- blockers such as missing answer, ambiguous grouping, unsupported target type, or rights basis;
- the exact Razbiram JSON preview and compatibility profile.

The convenience action “Create JSON” means “run extraction and open the review draft.” It must
not silently publish or export unverified answers.

## Initial limits

Concrete values remain configurable and should be measured in M0, with these conservative
starting points:

- 20 MiB per image;
- 100 MiB per PDF;
- 200 selected PDF pages per job;
- 1 MiB pasted text;
- 500 source artifacts per job;
- two extraction workers;
- cloud processing off until explicitly chosen.

Limits are checked before expensive decoding and are reported in plain language.
