# Security

## Reporting

Do not open a public issue for a vulnerability that could expose browser sessions, captures,
credentials, or private learning content. Contact the maintainer privately.

## Security model

The extensions, controlled browser, file/PDF importers, and local service process untrusted and
potentially sensitive content. The implementation must:

- bind the local API to loopback only;
- use a random per-launch origin token for UI-to-service calls;
- reject cross-origin WebSocket/HTTP requests;
- pair only through short-lived codes and accept only exact paired extension origins;
- require temporary active-tab access by default and keep optional origin grants revocable;
- never request cookies, history, debugger, `webRequest`, or `<all_urls>` by default;
- validate extension protocol version, tab/origin, command, nonce, hashes, and sizes;
- isolate each capture session in its own browser context and storage directory;
- never expose Chrome DevTools Protocol ports on a non-loopback interface;
- validate target schemes and block `file:`, `javascript:`, browser-internal pages, and loopback
  SSRF unless an explicit local-fixture mode is active;
- block downloads and unexpected pop-ups by default;
- redact credentials, tokens, cookies, form values, and authorization headers from logs;
- cap image dimensions, bytes, page count, job duration, model cost, and concurrent browsers;
- reject archive traversal, absolute paths, symlinks, hash mismatches, decompression bombs, and
  active PDF content;
- sanitize all captured HTML before rendering it in the review UI;
- never execute captured scripts in the review preview;
- store provider secrets only in environment or OS credential storage;
- make evidence retention visible, configurable, and deletable;
- provide a one-click session wipe.

Provider upload must be opt-in per session. The UI must state exactly which screenshot/derived
text will leave the machine before the first cloud call.

The extension stores no provider secret, does not upload to razbiram.com automatically, and does
not collect page content, origins, or browser history for analytics or marketing.

See `docs/architecture/SECURITY_PRIVACY_LEGAL.md` for the threat model and legal boundaries.
