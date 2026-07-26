# Identity algorithms

All stable identifiers in the pipeline are deterministic SHA-256 hashes of a precise byte
sequence. This document is the single authoritative specification. TypeScript (extension) and
Python (pipeline) implementations must produce byte-identical output from identical inputs; any
divergence is a bug, not a configuration difference.

## Text normalization

### Unicode form

Apply **NFC** (Canonical Decomposition followed by Canonical Composition) to all user-visible
text fields before hashing. Use NFKC only for mathematical operator symbols and compatibility
digits when explicitly noted.

### Whitespace collapse

1. Strip leading and trailing whitespace (Unicode category `Z*` and ASCII controls).
2. Collapse all interior runs of whitespace (including `\t`, `\r`, `\n`, ` `) to a single
   ASCII space `\x20`.

### Markup stripping

Exactly two steps, in this order:

1. **Strip tags.** Remove all XML/HTML tag content — characters between `<` and `>` inclusive.
2. **Decode entities.** Decode `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;` and numeric entities
   (`&#…;`, `&#x…;`) to their Unicode code points.

The order is load-bearing and must not be swapped. Decoding first turns `&lt;b&gt;` into `<b>`,
which the tag pass would then delete — destroying text the user actually saw. Stripping first
removes only real markup. For DOM-sourced text the distinction is moot, because the browser has
already decoded entities; it matters for raw HTML input such as pasted markup.

### Feedback annotation stripping (cleanText)

`cleanText` in `semantic-snapshot.v1` is the `visibleText` after removing correctness markers
that a reveal state may inject. Strip in this order:

1. **Leading Unicode markers**: remove any leading occurrence of U+2713 ✓, U+2714 ✔, U+2717 ✗,
   U+2718 ✘, U+25CF ●, U+25CB ○, U+2192 → followed by optional whitespace.
2. **Leading keyword markers**: case-insensitively remove a leading word that is exactly
   "correct", "incorrect", "right", or "wrong" when it is followed by a colon, period, or
   whitespace and the remaining text is non-empty.
3. **Trailing parenthetical markers**: remove a trailing substring matching the pattern
   `\s*\((?:correct|incorrect|right answer|wrong)\)\s*$` (case-insensitive).

Apply these rules after markup stripping and before whitespace collapse. The result is then
Unicode NFC-normalized and whitespace-collapsed. The Golden-Set case G13 is the acceptance test.

## Serialization protocol

All serialization is **UTF-8**, no BOM. Fields are joined with a newline (`\x0A`). Every prefix
label includes a trailing colon. SHA-256 is computed over the raw bytes of the assembled string.
Output is lowercase hexadecimal (64 characters). Prefixed IDs truncate to the indicated length.

## Algorithm definitions

### `questionFingerprint`

Join key. Identical across question and reveal states for the same question. Order-independent
across option randomization.

```
input:
  origin         NFC-normalized page origin (scheme + host, no path)
  path           NFC-normalized page path (no query, no fragment)
  card_family    ASCII lowercase card-family string
  question_text  markup-stripped, NFC, whitespace-collapsed question stem text
  option_texts   list of markup-stripped, feedback-stripped, NFC, whitespace-collapsed
                 option texts (cleanText values from nodes of nodeType "option")

algorithm:
  sorted_options = lexicographic sort of option_texts (Unicode code-point order)

  blob = join with "\n":
    "qfp:1"
    "origin:" + origin
    "path:" + path
    "family:" + card_family
    "question:" + question_text
    "option_count:" + str(len(sorted_options))
    "options:" + join(sorted_options, "\n")

  questionFingerprint = sha256(blob.encode("utf-8")).hexdigest()
```

G13 acceptance: sorting makes the fingerprint identical whether options appear in original or
randomized order. G14/G15 acceptance: identical content across rerenders or revisits yields
identical fingerprints.

### `stateFingerprint`

Dedup key for one specific DOM state. Distinct between question and reveal states; identical
across rerenders of the same semantic state.

```
input:
  questionFingerprint   the value computed above
  option_states         list of (cleanText, checked, visibleText) for each option node,
                        sorted by cleanText (same sort key as questionFingerprint options)
  explanation_text      markup-stripped, NFC, whitespace-collapsed text of all nodes with
                        nodeType "explanation", joined with "\n"; empty string if none

  per_option = join("|", [clean + ":" + str(int(checked)) + ":" + visible
                          for (clean, checked, visible) in option_states])

  blob = join with "\n":
    "sfp:1"
    "qfp:" + questionFingerprint
    "options:" + per_option
    "explanation:" + explanation_text

  stateFingerprint = sha256(blob.encode("utf-8")).hexdigest()
```

### `captureId`

Stable identity for one extension-capture event. Computed before the manifest is written.

```
input:
  created_at          ISO 8601 UTC timestamp (exact string as it appears in createdAt field)
  origin              NFC-normalized page origin
  path                NFC-normalized page path
  capture_state       captureState enum value string
  question_fp         questionFingerprint hex string
  artifact_hashes     list of sha256 hex strings from artifacts, sorted lexicographically

  blob = join with "\n":
    "cid:1"
    "created:" + created_at
    "origin:" + origin
    "path:" + path
    "state:" + capture_state
    "qfp:" + question_fp
    "artifacts:" + join(artifact_hashes, "\n")

  captureId = "cap_" + sha256(blob.encode("utf-8")).hexdigest()
```

### `sourceId`

Stable per-source-question identity used in Capture IR.

```
input:
  origin              NFC-normalized page origin
  path                NFC-normalized page path
  question_fp         questionFingerprint hex string

  blob = join with "\n":
    "sid:1"
    "origin:" + origin
    "path:" + path
    "qfp:" + question_fp

  sourceId = "src_" + sha256(blob.encode("utf-8")).hexdigest()[:32]
```

### `optionId`

Stable per-option identity. Derived from source and the option's cleaned text, not its display
position. Two options with identical cleanText on the same question produce a collision; the
validator reports this as a duplicate-option error rather than silently merging.

```
input:
  source_id           sourceId string
  clean_text          feedback-stripped, NFC, whitespace-collapsed option text

  blob = join with "\n":
    "oid:1"
    "source_id:" + source_id
    "clean_text:" + clean_text

  optionId = "opt_" + sha256(blob.encode("utf-8")).hexdigest()[:32]
```

### `cardId`

Stable per-card identity in the Capture IR. Derived from `sourceId` so it is independent of
reviewer actions (approval order, deck reordering). The export exporter may assign a
human-readable sequential label in the exported deck, but the canonical IR identity is
source-stable.

```
  cardId = "q-" + sha256(("crd:1\nsource_id:" + sourceId).encode("utf-8")).hexdigest()[:16]
```

## Cross-implementation requirements

- Implementations must include a self-test that computes all six identifiers for the Golden-Set
  fixture inputs and asserts byte-identical hex output.
- Any change to a normalization step, field list, separator, or prefix label is a breaking
  change that requires a new algorithm version (`qfp:2`, etc.) and a migration path.
- The TypeScript implementation runs in the extension service worker; it must not call any
  platform API that is unavailable in that context (no Node.js `crypto` module; use the Web
  Crypto API `SubtleCrypto.digest`).
- The Python implementation uses `hashlib.sha256` from the standard library.
- No implementation may log, cache, or transmit raw option texts or question stems outside the
  local artifact store.
