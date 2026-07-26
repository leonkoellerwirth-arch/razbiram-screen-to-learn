# Sources

No example screenshot or third-party learning content is included in this concept package.

Implementation fixtures must be:

- authored specifically for this project;
- licensed for redistribution; or
- synthetic.

Every non-original fixture or visual asset must record author, source URL, license, retrieval
date, and any modifications here.

## Fixtures in this repository

### `fixtures/images/quiz.png`

- **Origin:** synthetic. Rendered from `fixtures/images/quiz.html`, which was authored for this
  project, and captured with a headless browser at 1000×720.
- **Content:** four generic textbook facts (insulin, metals, photon rest mass) written for the
  fixture. No third-party question bank, no captured learning platform, no branding.
- **Licence:** same as the repository.
- **Why it is committed:** the OCR path cannot be tested without a real raster. The HTML source
  sits beside it so the image can be regenerated and its provenance checked rather than trusted —
  see `fixtures/images/README.md`.

## Architecture references

Primary platform documentation consulted on 2026-07-25:

- Chrome [`activeTab`](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab)
  and [`tabs.captureVisibleTab`](https://developer.chrome.com/docs/extensions/reference/api/tabs);
- MDN [WebExtension content scripts](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts);
- Chrome [Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging);
- Firefox [Native Messaging](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging);
- Apple [Safari extensions](https://developer.apple.com/safari/extensions/) and
  [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos)
  for the deferred Safari/native option.
