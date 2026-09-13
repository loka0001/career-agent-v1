# Design System

## Visual language

The interface uses a dark glassmorphism theme defined entirely by CSS variables:

- A fixed aurora backdrop (`.aurora`): layered radial gradients over `--canvas` with a subtle masked grid. It sits at `z-index: -2` and never intercepts pointer events.
- Glass surfaces: translucent panels (`--glass`, `--glass-border`) with `backdrop-filter: blur(18px) saturate(150%)`, a 1px light border, and an inset top highlight.
- One brand gradient (`--gradient-brand`, indigo → blue → cyan) reserved for primary actions, active navigation, chart fills, and key numbers.
- Status colors are translucent tints with light text (`--success-soft`/`--success-text`, warning, danger) tuned for WCAG AA on the dark canvas.

## Tokens

`web/src/styles/tokens.css` is the single source for colors, glass surfaces, gradients, spacing, radii, shadows, layout sizes (`--sidebar-width`, `--topbar-height`, `--max-width`), and typography. Components must use variables rather than isolated color values.

## Reusable components

| Component | Purpose |
| --- | --- |
| `Button` | Primary (gradient + glow), secondary (glass), destructive, and ghost actions with disabled state. |
| `Card` | Glass surface; `hover` prop adds lift + border emphasis. |
| `Alert` | Info, success, warning, and error feedback with accessible roles. |
| `Badge` | Product, publication, or integration status pill. |
| `Spinner` | Named loading state. |
| `Skeleton` | Shimmer placeholder for loading panels. |
| `StatCard` | Dashboard KPI: label, icon, large value, footnote. |
| `EmptyState` | Explains absence and gives a next action. |
| `ProductCard` | Product image, status badge, price, stock signal, optional ranking reasons. |
| `PlatformPreview` | Separate Facebook or Instagram post preview. |
| `icons.tsx` | Inline SVG icon set (no icon dependency, inherits `currentColor`). |

## Charts

Dashboard charts are dependency-free: category bars are plain divs driven by percentage widths (RTL-safe by construction), and the publishing donut is a single SVG with `role="img"` and an `aria-label`. Chart motion uses CSS transitions only and is disabled by `prefers-reduced-motion`.

## Layout

- Desktop app shell: sticky glass sidebar (inline-start) + sticky glass topbar.
- Below 860px the sidebar is replaced by a fixed bottom tab bar (`.mobile-nav`) with safe-area padding.
- The landing page uses a floating pill navigation and section-based scrolling.

## Rules

- One visually dominant action per step.
- Never use color as the only status signal.
- Never hide a platform failure behind a combined “success” message.
- Keep technical RAG and Meta details on the integration page, not in the core wizard.
- Use logical CSS properties so RTL and LTR share the same layout code.
- Respect `prefers-reduced-motion`: all animation is decorative and collapses to instant transitions.
