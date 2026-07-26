# Image fixtures

`quiz.png` is the raster the OCR path is tested against. It is **generated**, not collected, so its
provenance can be checked rather than trusted — see the entry in `../../SOURCES.md`.

## Regenerating

```sh
python -m http.server 8099 --directory fixtures/images   # any static server will do
# then, in a headless browser, load http://127.0.0.1:8099/quiz.html and capture the full page
```

Anything that produces a plain full-page screenshot works. The test asserts on what the pipeline
extracts — three questions, one per family, with their answer key — not on pixels, so a different
renderer or a slightly different size is fine as long as the text stays legible.

## Why an image at all

OCR cannot be exercised without one. Everything the drawn-structure reader does — typographic
roles, widget detection, emphasis colour — is tested from synthetic geometry in
`tests/test_screenshot.py` and needs no fixture.
