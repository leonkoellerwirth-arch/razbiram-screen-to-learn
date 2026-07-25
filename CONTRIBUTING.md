# Contributing

Read `AGENTS.md`, `BIBLE.md`, and the relevant decision records before changing architecture or
contracts.

## Principles

- Use synthetic or owned test content.
- Add a Golden-Set fixture for extraction behavior.
- Keep extraction and generated enrichment separate.
- Preserve field-level evidence.
- Do not claim target compatibility without a target integration test.
- Keep Chrome and Firefox behavior in the shared extension core and justify every new permission.
- Add bundle, protocol, and cross-browser fixtures when changing extension capture.
- Coordinate reviewed-deck schema changes in the razbiram-nlp hub; never copy/fork the hub
  contract locally.
- Anki mappings require a razbiram-anki round-trip fixture and an explicit capability entry.
- Use Conventional Commits.

## Pull requests

Include:

- the user-visible or contract outcome;
- affected paths/contracts;
- source and target capability impact;
- security/privacy impact;
- extension permission impact where applicable;
- reviewed-deck/razbiram-anki compatibility impact where applicable;
- tests and Golden cases run;
- screenshots only for owned/synthetic UI fixtures.

Do not include raw authenticated-page captures, cookies, provider prompts containing private
content, or credentials.
