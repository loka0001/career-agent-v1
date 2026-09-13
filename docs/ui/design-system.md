# Commerce Revenue Autopilot design system

Last updated: 2026-08-08

## Product character

The canonical interface is a dark-first, Arabic-first revenue operations workspace.
It follows `design.md`: deep graphite canvas, restrained blue-violet accents, layered
translucent surfaces, sharp information hierarchy, and compact operational density.
Light mode is a supported secondary presentation, not a separate visual system.

## Sources of truth

- Tokens: `web/src/styles/tokens.css`.
- Shell and route surfaces: `web/src/styles/admin.css`.
- Commerce and operational layouts: `web/src/styles/commerce.css` and
  `web/src/styles/operations.css`.
- Icons: Phosphor through `web/src/components/icons.tsx`; official provider marks use
  their official brand icons.
- Fonts: Manrope, IBM Plex Sans Arabic, and JetBrains Mono, bundled locally.

## Core tokens

| Role           | Dark                | Light               |
| -------------- | ------------------- | ------------------- |
| Canvas         | `#0A0B0F`           | `#F5F7FB`           |
| Raised canvas  | `#101218`           | `#FFFFFF`           |
| Primary text   | `#F7F8FC`           | `#11131A`           |
| Secondary text | `#A9AFBF`           | `#5D6473`           |
| Primary action | Apple blue gradient | Apple blue gradient |
| Success        | Emerald             | Emerald             |
| Warning        | Amber               | Amber               |
| Danger         | Rose                | Rose                |

Glass surfaces use semi-transparent fills, one-pixel borders, controlled blur, and a
solid fallback when backdrop filtering or transparency is unavailable. Reduced-motion
and reduced-transparency preferences are respected.

## Shared experience

- Grouped, collapsible sidebar on desktop; rail/tablet and drawer/mobile variants.
- Sticky top bar with route context, global command palette, locale, three-state theme selection,
  and profile actions. Notification claims remain absent until a real event source exists.
- Cards, buttons, badges, alerts, skeletons, empty states, tables, segmented controls,
  progress, pipelines, menus, and responsive master-detail layouts share the same
  tokens and focus treatment.
- Every visible primary action is functional or explicitly disabled with a truthful
  reason. Business data comes from the API or an explicitly labelled isolated demo.

## Responsive and bidirectional rules

- Desktop target: 1440 px; tablet target: 768 px; mobile target: 390 px.
- CSS must use logical properties. `web/scripts/check-logical-css.mjs` blocks physical
  left/right properties during `npm run lint`.
- Arabic and English share components; document `dir` and `lang` are switched by the
  i18n context.
- Focus indicators, keyboard-contained drawers, reduced motion, accessible names, and
  no horizontal overflow are release requirements.
