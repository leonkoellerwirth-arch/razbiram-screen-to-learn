# Fixture corpus

Self-contained synthetic page for testing the capture pipeline. No network, no build step.

## Open

```
open fixtures/pages/fixture.html        # macOS
xdg-open fixtures/pages/fixture.html   # Linux
```

Or load `file://<absolute-path>/fixtures/pages/fixture.html` directly in any browser.

## Question inventory

| Container ID        | Family           | Correct options                                           |
|---------------------|------------------|-----------------------------------------------------------|
| `q-single-choice`   | single-choice    | Vacuum                                                    |
| `q-multiple-select` | multiple-select  | Cellular organization, Metabolism, Response to stimuli    |
| `q-true-false`      | true-false       | True                                                      |
| `q-flashcard`       | flashcard        | back: "The coulomb (C) — defined as one ampere-second"    |
| `q-image-occlusion` | image-occlusion  | r1=Nucleus, r2=Mitochondria                               |

## Window API (Playwright / test driver)

```js
window.reveal('q-single-choice')     // transition container to reveal state
window.reshuffle('q-single-choice')  // shuffle option DOM order (G13)
window.rerender('q-multiple-select') // replace DOM nodes, keep semantics (G14)
window.navigate('q-flashcard')       // scroll + focus container (G15)
window.reset()                       // reset all containers to question state
```

All functions are synchronous except for the smooth-scroll inside `navigate`.

## GOLDEN_SET cases exercised

| Case | Control / selector                                          |
|------|-------------------------------------------------------------|
| G01  | `window.reveal('q-single-choice')` or "Reveal answer" btn  |
| G02  | `window.reveal('q-true-false')` or "Reveal answer" btn     |
| G03  | `window.reveal('q-multiple-select')` (no capability)       |
| G04  | `window.reveal('q-multiple-select')` (with capability)     |
| G07  | `window.reveal('q-flashcard')` or "Reveal back" btn        |
| G08  | `window.reveal('q-image-occlusion')` or "Reveal all" btn   |
| G13  | `window.reshuffle('q-single-choice')` then reveal          |
| G14  | `window.rerender('q-multiple-select')` (repeat N times)    |
| G15  | `window.navigate(idA); window.navigate(idB); window.navigate(idA)` |

G13 acceptance: `questionFingerprint` is identical before and after shuffle because
IDENTITY_ALGORITHMS.md sorts `cleanText` values before hashing.

G14 acceptance: `stateFingerprint` is identical across rerenders because semantic
content (cleanText, checked state) is unchanged; internal HTML `id` attributes differ.

G15 acceptance: navigating away and back yields the same `questionFingerprint` and
`stateFingerprint` because the DOM content is unchanged.

Feedback-stripping: in Q1 reveal state the correct option's `visibleText` is
`"✓ Vacuum"` while `cleanText` (via `data-clean-text`) remains `"Vacuum"`.
This exercises the leading-Unicode-marker stripping rule in IDENTITY_ALGORITHMS.md.

## Semantic hooks

Every question container has stable `id` and `data-question-id` attributes.
Every option `<li>` has a stable `data-option-id` attribute.
The `data-clean-text` attribute on each `.option-label` span is the pre-stripped
text used for fingerprinting. The `data-correct` attribute encodes ground truth
for test assertions.

Do not rely on internal element IDs that end in `-rr<N>` — those are re-keyed
by `window.rerender()` to simulate node replacement.
