# Quality and CI

## One gate

`./scripts/gate.sh` is the local and CI source of truth and ends with `GATE: PASS`.

Planned checks:

1. secret scan;
2. backend format/lint;
3. backend typecheck;
4. backend unit/contract/Golden tests;
5. frontend lint, token, UI-string, and LOC ratchets;
6. frontend typecheck/unit tests;
7. offline Playwright fixtures;
8. Chrome/Firefox extension unit, contract, manifest, and fixture tests;
9. schema generation drift check;
10. production studio and reproducible extension builds;
11. dependency audit.

CI is network-free after dependency installation. Real provider tests are marked `slow` and
never part of the required pull-request gate.

## Contract gates

- generated JSON Schemas match committed schemas;
- example JSON validates;
- migrations exist for any breaking Capture IR change;
- target profile Golden files round-trip through current product adapters;
- capability manifest cannot enable a capability without a linked integration test;
- deterministic exports match byte-for-byte Golden output;
- Chrome and Firefox capture manifests are semantically equivalent for shared fixtures;
- `.razcapture` validates and round-trips offline without changing hashes;
- generated Python and TypeScript contract types match committed schemas;
- the pinned reviewed-deck contract version matches the hub schema;
- cross-repo fixtures prove reviewed-deck → razbiram-anki → `.apkg` for supported families;
- unsupported Anki card families fail with a capability report rather than degrading.

JSON Schema cannot express the following cross-field constraints; they are code-validator duties:

- `correctOptionIds` is exactly the set of option ids where `isCorrect` is true;
- `meta.cardCount` equals `cards.length`;
- every `evidenceId` referenced in a card exists in the evidence ledger;
- single-choice `correctAnswer` equals the correct option's `text`;
- true/false cards have exactly two options;
- matching cards have referential integrity between pairs and unique item IDs across both sides;
- typed cards have at least one acceptable answer;
- image-occlusion media references exist and their content hashes match.

## Security gates

- gitleaks and private-key detection;
- no credential-like values in fixtures/history;
- dependency audit and SBOM;
- loopback/Origin/Host tests;
- extension pairing token, origin, nonce, replay, and revocation tests;
- permission budget rejects `<all_urls>`, cookies, history, debugger, and `webRequest` by default;
- archive traversal/symlink/decompression and hostile-PDF tests;
- URL sanitization and path traversal property tests;
- prompt-injection fixtures;
- artifact deletion test.

## Ratchets

- no new source file over 500 lines;
- no raw UI hex/neutral palette outside the token source;
- no hardcoded UI strings;
- no direct icon imports outside the icon gateway;
- bounded prompt/source-context size;
- no increase in existing warnings to silence a regression.

## Review checklist

Any change touching extension permissions/messages, browser navigation, local API pairing/auth,
provider calls, PDF parsing, captured HTML rendering, artifact download/upload, or retention
requires a security review.

Any change touching card interpretation requires:

- contract review;
- Capture IR migration assessment;
- target capability assessment;
- Golden case;
- product adapter/renderer test when applicable.

## Release criteria

- gate green on supported platforms;
- controlled-browser install/doctor and extension pairing checks documented;
- signed/reproducible Chrome and Firefox packages plus matching privacy disclosures;
- schema and app versions recorded;
- threat model reviewed;
- license/third-party notice current;
- no private fixture;
- changelog and migration notes;
- signed artifacts;
- rollback instructions.
