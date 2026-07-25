# Corporate identity

## Source of truth

Do not derive the new UI from screenshot-to-code branding or copy older sibling CSS blindly.

Current authority:

1. `../razbiram.com/app/src/styles/theme.css`
2. `../razbiram.com/app/src/styles/ui.css`
3. `../razbiram.com/docs/design/design_handoff_foundation/README.md`
4. `../razbiram.com/app/src/components/layout/BrandMark.tsx`
5. `../razbiram.com/docs/icons/razbiram-icon-CI.md`

Until a shared package exists, vendor a versioned token snapshot with:

- upstream repository and commit;
- © razbiram.com header;
- contract test for canonical token names and selected values;
- explicit update procedure.

This is the fourth family UI and triggers the Rule-of-Three case for a shared
`@razbiram/design-tokens` proposal. Extraction belongs in a Hub Mini-ADR, not an ad hoc copy.

## Brand

- outward name: `razbiram-screen-to-learn`;
- brand is lowercase `razbiram`;
- never display retired names such as StudyWithMe;
- use the canonical hub-and-four-spokes node mark;
- wordmark uses the canonical razbiram treatment plus a muted `-screen-to-learn` suffix;
- tagline, if used: “Bulgarian, until it clicks.” Do not invent pricing or product promises.

## Visual language

- warm, calm, confident, premium learning tool;
- dark is the shipped default; explicit light (`focus`) is respected;
- themes switch at the root with `data-theme`; no per-component dark palettes;
- warm coral primary (`#e2533c` light; live dark token from the current product);
- sage/good means mastered or strong;
- faint neutral means untouched/new;
- one dominant next action per phase;
- avoid rainbow status colors and cartoon gamification.

Never hardcode these values in components. Consume the versioned tokens or the `swm-*` bridge.

## Typography

- Manrope for UI and body;
- PT Serif for selective editorial/source content;
- Unbounded only for large numbers/status metrics;
- self-host fonts so local-first mode makes no unexpected network request;
- verify Bulgarian Cyrillic glyph coverage.

## Review studio layout

Desktop:

```text
┌──────────────── top bar: brand · browser/session · retention ────────────────┐
│ job/capture rail │ source evidence              │ extracted card + issues   │
│                  │ DOM / screenshot / reveal    │ type-aware editor          │
│                  │                              │ provenance + approval      │
├─────────────────────────────────────────────────────────────────────────────┤
│ previous · reject                         save draft · approve · next         │
└─────────────────────────────────────────────────────────────────────────────┘
```

Mobile becomes a phase-oriented flow, not three squeezed columns:

1. Evidence;
2. Card;
3. Issues/provenance;
4. Approve/next.

## Extension surfaces

The toolbar popup is a compact Razbiram product, not a miniature review studio.

```text
┌─ razbiram · screen-to-learn ─────────┐
│ Current tab: example.edu             │
│ [ Capture this question ]            │
│ [ Select region ]   Observe: Off     │
│ Studio: Paired · 2 captures queued   │
│ Privacy and permissions              │
└──────────────────────────────────────┘
```

- one coral primary action per state;
- active capture uses text, icon, and status—not color alone;
- the exact current origin is visible before capture/observe;
- permission requests explain purpose before the browser prompt;
- Capture Lite and paired mode are equally legible;
- the popup remains keyboard-complete at its minimum width;
- store icons and screenshots use the canonical mark and current tokens.

Razbiram discovery belongs to onboarding, store copy, and a quiet post-export link. Never inject
advertising into the source page or generated cards, and never use captured origin/content as
marketing data.

## Accessibility

- fully usable at 320–360 px;
- every control has a minimum 44 px target;
- real buttons, inputs, labels, fieldsets, radiogroups, and checkbox groups;
- visible focus and logical focus movement on phase changes;
- `aria-live` for job progress and export outcome;
- error summary links to invalid fields;
- screenshot evidence has textual extraction/alt context;
- do not use color alone for correctness or confidence;
- respect reduced motion;
- animated icons pass through the family icon gateway.

## Icons

Use one gateway modeled on the current `<AnimatedIcon>` system:

- 48-grid;
- 2.4 round stroke;
- warm ink plus at most one coral accent;
- shared motion primitives;
- reduced-motion fallback;
- no emoji icons and no direct icon-package imports in feature components.

The gateway and branded icon assets carry the visual-identity license carve-out.

## Internationalization and voice

- UI chrome through `t()` from the beginning;
- English and German baseline;
- learner-facing explanations are warm and direct;
- distinguish “source-verified”, “confirmed by you”, and “not yet proven” plainly;
- never imply AI certainty;
- code and README English, stakeholder/teacher guides additionally German.
