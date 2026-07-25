# Third-party notices

## screenshot-to-code

Architecture donor evaluated from:

- project: `abi/screenshot-to-code`
- repository: <https://github.com/abi/screenshot-to-code>
- reviewed commit: `6094fd710becd981fbcf29cfc32d7ebef921866d`
- license: MIT
- copyright: © 2023 Abi Raja

If substantial source is copied, the upstream MIT copyright and permission notice must accompany
the copied portion. Prefer small, traceable ports with a source comment naming the upstream file
and commit.

Candidate source areas:

- `backend/preview_screenshot/`: backend protocol, registry, availability probe, browser reuse;
- `backend/agent/providers/`: normalized streaming/provider adapters;
- `backend/uploaded_assets/store.py`: bounded image/data-URL validation;
- `backend/fs_logging/`: run recording patterns;
- `design-docs/agent-tool-calling-flow.md`: event lifecycle.

Do not copy product branding, hosted-only code, or unrelated code-generation prompts.

## razbiram visual identity

The razbiram name, logo, wordmark, design tokens, and branded visual theme are
© razbiram.com. They are used to keep a coherent family identity and are not sublicensed under
this repository's MIT code license.
