# Commerce Revenue Autopilot — Design System & Screen Specification

Version 1.0 · design.md

---

## 1. Product Design Principles

1. **Calm authority.** Merchants live in this product for hours a day. The UI should feel quiet and load-bearing, not decorative — glass surfaces signal depth and hierarchy, they never compete with the data underneath.
2. **Data first, chrome second.** Every glass panel exists to frame a number, a conversation, or a decision. If a surface doesn't carry information or an action, it doesn't get a border and a blur — restraint is the discipline that keeps "Liquid Glass" from tipping into decoration.
3. **One accent language.** Apple Blue is the only color that means "primary action" or "AI-generated." Violet/magenta gradients are reserved for AI-attributed content (suggestions, generated copy, automation activity) so merchants learn to read "gradient = the AI did this."
4. **Bidirectional by construction, not by patch.** Every spacing, icon-direction, and chart-orientation rule is defined once as a logical property (`start`/`end`, not `left`/`right`) so Arabic RTL is a mirrored first-class layout, not a translated afterthought.
5. **Never a dead end.** Every list, table, and panel has an explicit empty, loading, error, and (where relevant) locked/permission state designed before the "happy path" — this is enforced per-screen in Section 9.
6. **Trust is a design material.** Money, customer data, and AI-authored messages move through this product. Confirmation dialogs, audit trails, and security surfaces get the same visual care as the dashboard, not a bare system alert.

---

## 2. Color Tokens

Dark mode is the default and primary theme. Light mode is a supported secondary theme (tokens mirrored at the end of this section). All pairings below meet WCAG AA (4.5:1 body text, 3:1 large text/icons) against their specified surface.

### 2.1 Core Palette — Dark (default)

| Token | Hex / RGBA | Usage |
|---|---|---|
| `--color-bg-base` | `#0A0B0F` | App canvas, behind all glass layers |
| `--color-bg-elevated` | `#111319` | Sidebar, top nav base (pre-blur) |
| `--color-surface-glass-1` | `rgba(255,255,255,0.055)` | Level-1 glass card fill |
| `--color-surface-glass-2` | `rgba(255,255,255,0.09)` | Level-2 glass card fill (modals, popovers) |
| `--color-surface-glass-3` | `rgba(255,255,255,0.14)` | Level-3 glass fill (active/hover state of level-1/2) |
| `--color-border-glass` | `rgba(255,255,255,0.12)` | Default glass border |
| `--color-border-glass-strong` | `rgba(255,255,255,0.22)` | Focus/active glass border |
| `--color-text-primary` | `#F5F6FA` | Headings, primary content, contrast 15.8:1 on base |
| `--color-text-secondary` | `#AEB3C2` | Supporting text, contrast 7.1:1 on base |
| `--color-text-tertiary` | `#787E90` | Metadata, timestamps, contrast 4.6:1 on base |
| `--color-text-disabled` | `#4B4F5C` | Disabled labels (non-text-bearing controls only) |
| `--color-accent-blue` | `#0A84FF` | Primary — Apple Blue, buttons, links, focus rings |
| `--color-accent-blue-hover` | `#3B9EFF` | Primary hover |
| `--color-accent-blue-active` | `#0868CC` | Primary pressed |
| `--color-accent-violet` | `#8B5CF6` | AI accent gradient stop |
| `--color-accent-magenta` | `#C74FD1` | AI accent gradient stop (used sparingly, ≤10% of a gradient's visual weight) |
| `--color-success` | `#30D48A` | Success states, positive deltas |
| `--color-success-bg` | `rgba(48,212,138,0.14)` | Success badge/alert fill |
| `--color-warning` | `#F5A623` | Warning states |
| `--color-warning-bg` | `rgba(245,166,35,0.14)` | Warning badge/alert fill |
| `--color-danger` | `#FF5C5C` | Destructive actions, errors, negative deltas |
| `--color-danger-bg` | `rgba(255,92,92,0.14)` | Danger badge/alert fill |
| `--color-info` | `#5AC8FA` | Informational badges (distinct from primary blue) |

### 2.2 Gradient Tokens

| Token | Definition | Usage |
|---|---|---|
| `--gradient-primary` | `linear-gradient(135deg, #0A84FF 0%, #6E7CF6 100%)` | Primary CTA fill, active nav indicator |
| `--gradient-ai` | `linear-gradient(135deg, #0A84FF 0%, #8B5CF6 55%, #C74FD1 100%)` | AI-generated content markers, Agent avatar ring, Studio generate button |
| `--gradient-glow-blue` | `radial-gradient(circle, rgba(10,132,255,0.35) 0%, rgba(10,132,255,0) 70%)` | Ambient hero/background glow, landing page |
| `--gradient-mesh-hero` | `radial-gradient(at 20% 20%, rgba(10,132,255,0.25) 0, transparent 50%), radial-gradient(at 80% 0%, rgba(139,92,246,0.20) 0, transparent 50%), radial-gradient(at 50% 100%, rgba(199,79,209,0.10) 0, transparent 50%)` | Landing/auth page background mesh |
| `--gradient-border-ai` | `linear-gradient(135deg, rgba(10,132,255,0.6), rgba(199,79,209,0.6))` | 1px animated border on AI-authored cards (via mask technique) |

### 2.3 Light Mode Mirror

| Token | Hex / RGBA |
|---|---|
| `--color-bg-base` | `#F3F4F7` |
| `--color-bg-elevated` | `#FFFFFF` |
| `--color-surface-glass-1` | `rgba(255,255,255,0.65)` (blur over base) |
| `--color-surface-glass-2` | `rgba(255,255,255,0.80)` |
| `--color-border-glass` | `rgba(15,17,23,0.10)` |
| `--color-text-primary` | `#14161C` |
| `--color-text-secondary` | `#4B4F5C` |
| `--color-text-tertiary` | `#787E90` |
| `--color-accent-blue` | `#0066E0` (darkened 1 step for AA on white) |
| success/warning/danger hues unchanged, backgrounds lightened to 10% alpha on white. |

---

## 3. Typography Scale

**Primary family:** Manrope (Latin) paired with **IBM Plex Sans Arabic** for RTL content — both are geometric, low-contrast sans faces with matching x-height so LTR/RTL paragraphs feel like one type system rather than two fonts stitched together. **Monospace:** JetBrains Mono, for API keys, order IDs, webhook payloads.

`font-family: 'Manrope', 'IBM Plex Sans Arabic', -apple-system, 'Segoe UI', sans-serif;`

| Token | Size / Line-height | Weight | Usage |
|---|---|---|---|
| `--text-display` | 40px / 48px | 700 | Landing hero only |
| `--text-h1` | 28px / 36px | 700 | Page titles |
| `--text-h2` | 22px / 30px | 700 | Section headings, drawer titles |
| `--text-h3` | 18px / 26px | 600 | Card titles, modal titles |
| `--text-body-lg` | 16px / 24px | 500 | Emphasized body, form labels |
| `--text-body` | 14px / 20px | 400 | Default UI text |
| `--text-body-sm` | 13px / 18px | 400 | Table cells, secondary metadata |
| `--text-caption` | 12px / 16px | 500 | Badges, timestamps, helper text |
| `--text-metric` | 32px / 38px | 700 | KPI numbers (tabular-nums) |
| `--text-metric-sm` | 20px / 26px | 700 | Secondary metric numbers |

Rules: Arabic UI text never uses weight below 500 (Plex Sans Arabic reads lighter at equivalent weight than Manrope). Numerals in both languages render as Western Arabic numerals with `font-feature-settings: 'tnum'` for column alignment in tables and metrics.

---

## 4. Spacing & Sizing Tokens

8px base grid.

| Token | Value |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |

**Layout constants:** Sidebar expanded `280px` / collapsed `72px`. Top nav height `64px`. Content max-width `1440px` (centered on ultra-wide). Drawer width `480px` (desktop), full-width (mobile). Modal widths: sm `420px`, md `560px`, lg `760px`.

---

## 5. Radius, Border, Blur, Shadow, Gradient Tokens

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 10px | Badges, inputs, small buttons |
| `--radius-md` | 16px | Buttons, table rows, list items |
| `--radius-lg` | 20px | Cards, panels |
| `--radius-xl` | 24px | Modals, drawers, hero panels |
| `--radius-full` | 999px | Avatars, pills, icon buttons |
| `--blur-glass` | `backdrop-filter: blur(24px) saturate(140%)` | Standard glass surface |
| `--blur-glass-heavy` | `backdrop-filter: blur(40px) saturate(160%)` | Top nav, modals over busy backgrounds |
| `--border-glass` | `1px solid var(--color-border-glass)` | Default card border |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.24)` | Buttons, inputs |
| `--shadow-md` | `0 8px 24px rgba(0,0,0,0.32)` | Cards at rest |
| `--shadow-lg` | `0 16px 48px rgba(0,0,0,0.44)` | Modals, drawers, popovers |
| `--glow-focus` | `0 0 0 3px rgba(10,132,255,0.35)` | Focus ring, layered outside border |
| `--glow-ai-soft` | `0 0 24px rgba(139,92,246,0.18)` | AI-panel ambient glow (used once per view max) |

Glow is restrained by rule: at most one ambient glow element per screen, always behind content, never on hover for non-AI elements.

---

## 6. Responsive Breakpoints

| Token | Range | Layout behavior |
|---|---|---|
| `--bp-mobile` | 0–767px | Single column, bottom-accessible nav drawer, drawers/modals go full-screen |
| `--bp-tablet` | 768–1199px | Sidebar auto-collapses to icon rail; two-column max; three-column views (Inbox) become two-pane with a slide-over |
| `--bp-desktop` | 1200–1599px | Full shell, three-column layouts active |
| `--bp-wide` | 1600px+ | Content max-width caps at 1440px, extra space becomes side margin, never stretched tables |

---

## 7. Application Shell Specification

### 7.1 Desktop Sidebar (collapsible: 280px ⇄ 72px)
- Glass fill `--color-surface-glass-1` over `--color-bg-elevated`, right border in LTR / left border in RTL (`--border-glass`).
- Top: workspace selector (logo mark + workspace name + chevron → popover with workspace list, "Create workspace").
- Middle: nav groups — **Workspace** (Command Center, Inbox, Opportunities, Customers, Products, Orders), **Grow** (Content Studio, Campaign Calendar, Analytics, Automations, Agent Settings), **Manage** (Integrations, Team, Billing, Store Settings, Security, API Keys). Group labels in `--text-caption`/`--color-text-tertiary`, hidden when collapsed.
- Operator Console appears as a distinct, visually separated bottom section with a subtle amber-tinted glass fill, only rendered when `user.role === 'operator'`.
- Active item: `--gradient-primary` at 12% opacity fill, `--radius-md`, 3px start-edge indicator bar in solid `--color-accent-blue`.
- Collapse toggle pinned to sidebar bottom edge; collapsed state shows icons only with tooltip-on-hover labels.
- Item states: Default (secondary text, transparent) → Hover (`--color-surface-glass-2`, primary text) → Active (as above) → Focus (glow-focus ring) → Disabled (locked plan features show a small lock glyph, 40% opacity, tooltip "Available on Growth plan").

### 7.2 Mobile Navigation Drawer
- Triggered from top nav hamburger. Full-height slide-in from start-edge, `--blur-glass-heavy`, covers 88% width, scrim `rgba(0,0,0,0.5)` on remaining 12%.
- Same grouped structure as desktop sidebar, larger tap targets (48px row height minimum).
- Closes on scrim tap, swipe-to-close (swipe toward start edge), or route change.

### 7.3 Top Navigation Bar (glass, 64px, sticky)
- `--blur-glass-heavy`, bottom border `--border-glass`, sits above content with `z-index` above cards but below modals.
- Start: hamburger (mobile only) / sidebar-collapse toggle (desktop) + breadcrumb trail.
- Center-start: global search trigger — pill-shaped `--radius-full` input-look button, `⌘K` hint, opens Command Palette.
- End cluster (end-to-start order in LTR, mirrored in RTL): notification bell (badge dot for unread, badge count >9 shows "9+"), language switcher (flag-free — text toggle "EN / AR"), theme switcher (sun/moon icon, 3-state: light/dark/system), user profile menu (avatar + chevron → popover: profile, workspace settings, sign out).

### 7.4 Command Palette (⌘K / Ctrl+K)
- Centered modal, `--radius-xl`, `--blur-glass-heavy`, max-width 640px, top-anchored at 15% viewport height.
- Fuzzy search across screens, customers, orders, products, actions ("Create product", "Invite team member"). Grouped results with section labels. Arrow-key + Enter navigation, `Esc` to close.

### 7.5 Notification Menu
- Popover from bell icon, 380px width, tabs: All / Mentions / System. Each item: icon-by-type, message, relative timestamp, unread dot. "Mark all as read" footer action. Empty state: muted bell illustration + "You're all caught up."

### 7.6 Breadcrumb & Page Title System
- Pattern: `Workspace name / Section / Current page` as `--text-body-sm` breadcrumb above an `--text-h1` page title row, which also hosts primary page actions (end-aligned in LTR, start-aligned in RTL... i.e. always trailing-edge).

### 7.7 Loading Skeletons
- Shimmer: a `--gradient-primary`-tinted diagonal sweep at 6% opacity animating start→end over a `rgba(255,255,255,0.06)` base block, 1.4s ease-in-out loop, `prefers-reduced-motion` disables the sweep and shows a static pulse (opacity 0.5↔0.7, 1.8s).
- Skeleton shapes mirror real content geometry (table rows, KPI card blocks, avatar circles) — never a generic gray box unrelated to final layout.

### 7.8 Empty States
- Icon or small illustration (line-style, single-color `--color-text-tertiary`, 64px), `--text-h3` headline in interface voice ("No orders yet"), one-line supporting text explaining why and what happens next, one primary action when applicable.

### 7.9 Error States
- Inline (row/card level): `--color-danger` icon + short message + "Retry" text button.
- Full-panel: centered icon, `--text-h3` "Something needs your attention" pattern (screen-specific), Retry primary button, secondary "Contact support" link.

### 7.10 Confirmation Dialogs
- Modal sm (420px), icon reflects severity (info blue / warning amber / danger red), single-sentence question as title, one-line consequence text, Cancel (ghost) + confirm (danger/primary per action) buttons. Destructive confirmations require typing the entity name for irreversible actions (delete store, delete account).

### 7.11 Toast Notifications
- Stack at bottom-end corner (mirrors in RTL to bottom-start), `--radius-md` glass pill, auto-dismiss 5s (paused on hover/focus), max 3 stacked with "+N more" collapse. Success/warning/danger/info left-edge (start-edge) color bar 3px.

### 7.12 Form Validation States
- Default → Focus (`--glow-focus` + border `--color-accent-blue`) → Valid (subtle green check icon, border unchanged unless re-validated) → Invalid (border `--color-danger`, helper text in danger color with icon, `aria-invalid="true"`) → Disabled (reduced opacity, no interaction).
- Validation fires on blur for first pass, then live on change once a field has been touched and errored once.

### 7.13 Locked Feature / Paywall State
- Card or full-panel overlay: `--blur-glass` frosted overlay above the (still-visible, non-interactive) feature preview, centered lock badge in `--gradient-ai`, headline naming the feature, plan requirement, "Upgrade plan" primary CTA, "Learn more" ghost link.

### 7.14 Offline / Connection-Lost State
- Slim banner pinned under top nav, `--color-warning-bg` fill, icon + "You're offline — changes will sync when you're back" text, auto-hides on reconnect with a brief `--color-success-bg` "Back online" confirmation banner (3s).

---

## 8. Component Specifications & States

All interactive components define: **Default, Hover, Focus, Active, Disabled, Loading, Error** (where applicable). Focus is always a visible `--glow-focus` ring, never removed, meeting 3:1 non-text contrast (WCAG 2.4.11).

### 8.1 Buttons
- **Primary:** `--gradient-primary` fill, white text, `--radius-md`, `--shadow-sm`. Hover: brightness +8%, `--shadow-md`. Active: brightness −6%, scale 0.98. Disabled: 40% opacity, no shadow. Loading: spinner replaces label, width preserved.
- **Secondary:** `--color-surface-glass-2` fill, `--border-glass-strong`, primary text. Hover: fill → glass-3.
- **Ghost:** transparent, secondary text, underline-free. Hover: `--color-surface-glass-1` fill.
- **Danger:** solid `--color-danger`, white text; same state ladder as primary.
- **Icon button:** 40×40px, `--radius-full`, transparent default, `--color-surface-glass-2` on hover, tooltip on 400ms hover delay.

### 8.2 Inputs
- **Text field:** 44px height, `--radius-sm`, `--color-surface-glass-1` fill, `--border-glass`. Label above (`--text-body-sm`, secondary). Helper/error text below.
- **Password field:** trailing eye-toggle icon button; strength meter (signup) as 4-segment bar beneath, colored `--color-danger → --color-warning → --color-info → --color-success`.
- **Select:** same shell as text field + chevron, opens glass popover listbox with checkmark on selected.
- **Textarea:** min 96px, resizable vertical only.
- **File upload:** dashed `--border-glass-strong` dropzone, `--radius-lg`, center icon+label, drag-active state swaps border to solid `--color-accent-blue` + `--color-surface-glass-2` fill.

### 8.3 Glass Cards & Metric Cards
- Card: `--color-surface-glass-1`, `--border-glass`, `--radius-lg`, `--shadow-md`, `--blur-glass`. Hover (when clickable): border → `--border-glass-strong`, translateY(-2px).
- Metric card: label (`--text-caption`, tertiary) → value (`--text-metric`, tabular-nums) → delta chip (success/danger background pill with ▲/▼ glyph, never color-alone — always paired with the glyph for colorblind accessibility).

### 8.4 Tables (with mobile alternative)
- Desktop: glass header row (sticky), `--text-body-sm` cells, row hover `--color-surface-glass-1`, row height 52px, zebra disabled (glass handles separation via 1px `--border-glass` row dividers).
- Mobile alternative: rows collapse into stacked glass cards, each showing label:value pairs for the 3 most important columns + a "View details" chevron, replicating table semantics via `role="table"`/`aria-*` on the underlying markup even when visually a card list.
- Sort: clickable header with arrow glyph; Selection: leading checkbox column with bulk-action bar sliding down from header when ≥1 row selected.

### 8.5 Tabs
- Underline style: `--text-body`, secondary text, active tab primary text + 2px `--color-accent-blue` underline sliding on change (respecting reduced motion). Horizontal scroll on mobile overflow with edge fade masks.

### 8.6 Badges & Status Indicators
- Pill, `--radius-full`, `--text-caption` weight 600, colored background at 14% opacity + full-opacity text/dot of same hue. Status dot (8px circle) precedes label for connection/order states: Connected/Success = green, Pending/Syncing = blue (pulsing animation), Error/Disconnected = red, Draft/Neutral = gray.

### 8.7 Dropdown Menus
- Glass popover, `--radius-md`, `--blur-glass-heavy`, `--shadow-lg`, min-width 200px, items 40px height with leading icon slot, destructive items separated by divider and rendered in `--color-danger`.

### 8.8 Tooltips
- Dark solid (`#1C1E27`, not glass — tooltips need full legibility over any background), `--radius-sm`, `--text-caption`, 4px offset, 400ms show delay / 0ms hide delay, arrow pointer.

### 8.9 Drawers
- Slide in from end-edge (mirrors to start-edge in RTL), 480px desktop / full-screen mobile, `--blur-glass-heavy`, `--shadow-lg`, scrim behind. Header sticky with title + close icon button; footer sticky with primary/secondary actions when the drawer is a form.

### 8.10 Modals
- Centered, scrim `rgba(0,0,0,0.6)`, `--radius-xl`, `--blur-glass-heavy`, entrance: fade + scale from 0.96→1 (180ms ease-out), focus-trapped, `Esc` closes non-destructive modals only.

### 8.11 Toasts / Alerts
- Toast: see 7.11. Alert (inline, persistent): full-width banner variant of the toast visual language, used inside forms/pages for standing warnings (e.g., "Your trial ends in 3 days").

### 8.12 Pagination
- Numbered pill buttons + prev/next chevrons (chevrons flip direction in RTL), current page in `--gradient-primary` fill; "Rows per page" select at the opposite end.

### 8.13 Charts
- Library-agnostic spec: line/area charts use `--color-accent-blue` primary series with a soft area fill gradient (`--color-accent-blue` 20%→0% opacity vertical), gridlines `rgba(255,255,255,0.06)`, axis labels `--text-caption`/tertiary. Multi-series adds violet then success/warning/info in that order. Tooltips on hover use the dark solid tooltip style (8.8). All charts include a text-equivalent data table available via a "View as table" toggle for accessibility.

### 8.14 Date Picker
- Glass popover calendar, `--radius-lg`, current day outlined, selected day/range filled `--gradient-primary`, range-in-between at 12% blue tint. Preset shortcuts column (Today, 7d, 30d, This month, Custom) on the start-edge side, calendar grid on end-edge — mirrors in RTL.

### 8.15 Integration Cards
- Logo tile (44px, white/neutral card behind third-party logos for contrast safety regardless of theme) + name + status badge (8.6) + last-synced timestamp + action row (Connect/Configure/Reconnect/Disconnect as contextual button set) + expandable error detail panel.

### 8.16 Conversation Messages (Inbox)
- Customer message: start-aligned, `--color-surface-glass-1` bubble, `--radius-lg` with sharp start-corner.
- Merchant/agent message: end-aligned, `--gradient-primary` at 90% opacity bubble, white text, sharp end-corner.
- AI-suggested (not yet sent): dashed `--gradient-border-ai` outline bubble, ghost fill, "AI suggested" caption label + Accept/Edit/Discard inline actions.
- Channel glyph (WhatsApp/Messenger/Instagram) as a small badge at the bubble's outer corner.

### 8.17 Command Palette
- See 7.4.

### 8.18 Locked-Feature Card
- See 7.13, card-scoped variant: same frosted-overlay pattern constrained to a single card rather than full panel.

### 8.19 Confirmation Dialog
- See 7.10.

---

## 9. Screen Specifications (31 Screens)

Legend for state coverage: **L**oading, **E**mpty, **Er**ror, **S**uccess, **P**ermission.

### A. Public Website

#### 1. Landing Page — `/`
- **Purpose:** Convert visiting merchants into signups; explain the AI commerce automation value prop.
- **Layout:** Full-bleed single column, `--gradient-mesh-hero` background, sections stacked with `--space-16` rhythm, max-width 1200px inner container.
- **Sections:** Glass top nav (transparent→solid on scroll) · Hero (headline + subhead + primary "Start free" CTA + secondary "Watch demo" ghost button + animated product preview mock in a glass frame with floating mini metric cards) · Capability grid (6 glass cards: Inbox, Opportunities, Studio, Analytics, Automations, Integrations) · Integration logos strip (Shopify, WooCommerce, Meta, WhatsApp, Instagram, Stripe) · AI workflow explainer (3-step horizontal flow diagram: "Customer messages → AI drafts & routes → You approve or it auto-resolves") · Security/trust section (SOC2-style badges row, encryption/data-residency copy) · Pricing preview (3 plan cards, "See full pricing" link) · Final CTA band (`--gradient-primary` background block) · Footer (sitemap columns, Terms/Privacy links, language switcher, social links).
- **Reused components:** Buttons, Glass cards, Integration cards (simplified), Tabs (pricing monthly/annual toggle).
- **Actions:** Sign up, Log in, Watch demo (opens video modal), Switch language/theme.
- **Data displayed:** Marketing copy, illustrative (non-live) metrics in the preview mock, labeled "Example data."
- **States — L:** hero preview mock has its own shimmer skeleton before assets load. **E:** n/a. **Er:** video modal failed-to-load state with retry. **S:** n/a. **P:** n/a (public).
- **Desktop/tablet/mobile:** Desktop 3-col capability grid → tablet 2-col → mobile 1-col stacked, hero preview mock scales down and drops floating mini-cards on mobile.
- **RTL:** Full mirror; hero preview mock content re-renders with RTL sample UI rather than flipping an LTR screenshot.

#### 2. Login — `/login`
- **Purpose:** Authenticate returning users.
- **Layout:** Centered glass card (420px) over `--gradient-mesh-hero`, split-screen on desktop (brand panel start-edge, form end-edge) collapsing to single column below tablet.
- **Sections:** Logo · "Welcome back" heading · Email field · Password field (with visibility toggle) · Remember-me checkbox + Forgot-password link row · Primary "Log in" button · Divider · "Don't have an account? Sign up" link.
- **Reused components:** Text field, Password field, Buttons, Alert (for errors).
- **Actions:** Submit login, Toggle password visibility, Navigate to signup/forgot-password.
- **Data displayed:** None persisted.
- **States — L:** button shows loading spinner, fields disabled during submit. **E:** n/a. **Er:** inline Alert above form "Incorrect email or password" (generic, doesn't reveal which); after repeated failures, rate-limit Alert "Too many attempts — try again in 0:47" with live countdown, submit disabled. **S:** redirect on success, brief success toast on landing. **P:** n/a.
- **Desktop/tablet/mobile:** Brand panel hidden below 900px; mobile form is full-width with `--space-6` page padding.
- **RTL:** Form mirrors; brand panel copy right-aligns to the panel's leading edge (start).

#### 3. Signup — `/signup`
- **Purpose:** Create merchant account.
- **Layout:** Same split-screen shell as Login, taller form.
- **Sections:** Name, Business name, Email, Password (+ strength meter), Confirm password, Terms checkbox (with inline Terms/Privacy links), Primary "Create account" button, "Already have an account? Log in" link.
- **Reused components:** Text field, Password field, Buttons, Form validation states.
- **Actions:** Submit signup, Accept terms, Navigate to login.
- **States — L:** submit button loading. **E:** n/a. **Er:** per-field validation (weak password, mismatched confirmation, invalid email format) inline; duplicate-email Error message under the email field ("An account with this email already exists" + "Log in instead" link). **S:** redirect to Verify Email screen. **P:** n/a.
- **Desktop/tablet/mobile:** Same as Login.
- **RTL:** Mirrored; strength meter segments fill start→end.

#### 4. Verify Email — `/verify-email`
- **Purpose:** Confirm ownership of signup email.
- **Layout:** Centered glass card (420px), no split panel — single focused task.
- **Sections:** Envelope icon (`--gradient-ai` tinted) · "Verify your email" heading · Explainer text with masked email · 6-digit code input (segmented boxes) · Primary "Verify" button · "Resend code" text button with countdown (60s).
- **Reused components:** Buttons, Alert.
- **Actions:** Enter code, Resend code, Auto-submit on 6th digit.
- **States — L:** verifying spinner replaces button label. **E:** n/a. **Er:** invalid-code shake animation + red border + "That code isn't right" message; expired-code state swaps primary content to "This code expired — Resend a new one." **S:** success checkmark animation → auto-redirect to onboarding after 1.5s, with "Continue" button as fallback if motion reduced. **P:** n/a.
- **Desktop/tablet/mobile:** Code boxes shrink from 56px to 44px width on mobile, remain single row.
- **RTL:** Code entry direction stays LTR (numeric convention) inside an otherwise RTL-mirrored card, per standard bidi digit handling.

#### 5. Forgot Password — `/forgot-password`
- **Purpose:** Initiate password reset without leaking account existence.
- **Layout:** Centered glass card (420px).
- **Sections:** "Reset your password" heading · Explainer · Email field · Primary "Send reset link" button · Back-to-login link.
- **Actions:** Submit email.
- **States — L:** button loading. **E:** n/a. **Er:** only client-side format validation is shown; server never confirms/denies existence. **S:** form replaced with a neutral confirmation panel: "If an account exists for that email, we've sent a reset link" + envelope icon + "Back to login" button. **P:** n/a.
- **Desktop/tablet/mobile:** Standard centered-card scaling.
- **RTL:** Mirrored.

#### 6. Reset Password — `/reset-password`
- **Purpose:** Set a new password from an emailed token link.
- **Layout:** Centered glass card (420px).
- **Sections:** "Choose a new password" heading · New password field + strength meter · Confirm password field · Requirements checklist (live-checked items: 8+ chars, number, symbol) · Primary "Reset password" button.
- **Actions:** Submit new password.
- **States — L:** button loading, token validity pre-checked on mount (skeleton over form while checking). **E:** n/a. **Er:** expired/invalid token replaces the entire form with an Error panel: "This link has expired" + "Request a new link" button (routes to Forgot Password). **S:** success panel with checkmark + "Password updated" + "Log in" button. **P:** n/a.
- **Desktop/tablet/mobile:** Standard.
- **RTL:** Mirrored.

#### 7. Accept Team Invitation — `/accept-invite`
- **Purpose:** Let an invited user join a workspace.
- **Layout:** Centered glass card (460px).
- **Sections:** Workspace logo/name · "Inviter name invited you to join Workspace as Role" statement · Role badge · Accept (primary) / Decline (ghost) buttons · Below, conditionally: if no account exists, a compact name+password form to create one inline; if account exists, a "Log in to accept" prompt.
- **Actions:** Accept, Decline, Create account inline, Log in.
- **States — L:** invite lookup skeleton on mount. **E:** n/a. **Er:** expired invite panel ("This invitation has expired — ask [inviter] to send a new one"); invalid/already-used invite panel with distinct copy and a "Go to homepage" action. **S:** accept → redirect to workspace onboarding-complete or dashboard; decline → neutral confirmation "Invitation declined." **P:** n/a.
- **Desktop/tablet/mobile:** Standard centered card.
- **RTL:** Mirrored; inviter statement re-flows for Arabic grammar order (not a literal word-swap).

#### 8. Terms and Conditions — `/terms`
- **Purpose:** Legal document reading.
- **Layout:** Two-column desktop (sticky start-edge TOC 240px + end-edge content column, max-width 760px); single column mobile with a collapsible "On this page" accordion at top.
- **Sections:** Title + "Last updated" date · Sticky TOC (auto-generated from headings, active-section highlight on scroll) · Legal body content (numbered sections) · Contact details block · "Back to home" link.
- **Actions:** Jump-to-section via TOC, Back to home.
- **States — L:** content skeleton (paragraph-shaped blocks) while fetched. **E:** n/a. **Er:** fetch-failure panel with Retry. **S:** n/a. **P:** n/a.
- **Desktop/tablet/mobile:** TOC collapses to accordion below 900px.
- **RTL:** TOC moves to end-edge (visually right becomes the mirrored "start"); scroll-highlight logic unaffected.

#### 9. 404 Page
- **Purpose:** Handle unmatched routes gracefully.
- **Layout:** Centered, full-viewport, `--gradient-mesh-hero` background.
- **Sections:** Abstract glass-shard illustration (geometric, on-brand, not a cartoon) · "404 — Page not found" · One-line explanation · "Return home" (primary) + "Go to dashboard" (secondary) buttons.
- **States:** Static, no data states apply.
- **Desktop/tablet/mobile:** Illustration scales down, buttons stack vertically on mobile.
- **RTL:** Mirrored; illustration itself is direction-neutral (abstract, not text-bearing).

#### 10. 500 Page — `/500`
- **Purpose:** Handle server errors gracefully.
- **Layout:** Same centered shell as 404.
- **Sections:** Error glyph (triangle, `--color-danger` tinted glass) · "Something went wrong on our end" · Support reference ID (monospace, copyable) · "Retry" (primary) + "Return home" (secondary) buttons.
- **States:** Retry shows loading spinner briefly then either resolves or reloads the same panel.
- **Desktop/tablet/mobile:** Standard centered scaling.
- **RTL:** Mirrored; reference ID stays LTR (alphanumeric convention).

### B. Onboarding

#### 11. Onboarding Wizard — `/app/onboarding`
- **Purpose:** Guide a new workspace from signup to a working, connected setup.
- **Layout:** Full-screen focused shell (no sidebar) — glass top bar with logo + progress + "Save & exit" — centered content column (640px) — sticky footer with Back/Skip/Continue.
- **Sections/Steps:** 1. Business profile (name, industry, size) · 2. Store platform selection (Shopify/WooCommerce/None-yet as glass selectable cards) · 3. Store connection (OAuth-style connect flow or manual API key form depending on platform) · 4. WhatsApp/Meta connection (connect buttons + permission scopes list) · 5. AI assistant configuration (name, tone selector, language checklist) · 6. Product/catalog sync (progress bar with live item count as it imports) · 7. Team invitation (email chips + role select, skippable) · 8. Completion checklist (recap card list with checkmarks, "Go to Command Center" primary CTA).
- **Reused components:** Buttons, Select, Text field, Integration cards (compact), Progress indicator (segmented bar, one segment per step), Skeleton (sync step).
- **Actions:** Continue, Back, Skip (steps 3,4,7 explicitly skippable), Save & exit (resumable).
- **Data displayed:** Live sync counts (step 6), connection status per integration (steps 3–4).
- **States — L:** step 6 shows a live progress bar + streaming item count; connection steps show a "Connecting…" spinner state on the OAuth card. **E:** n/a (steps have defaults). **Er:** connection-failure card per step ("Couldn't connect to Shopify — check your store URL" + Retry + "Skip for now"); sync-failure partial state ("214 of 500 products imported — 12 failed" with "View details" link). **S:** each step shows a checkmark transition before advancing; step 8 is itself the success/completion state. **P:** n/a.
- **Desktop/tablet/mobile:** Content column narrows to full-width minus `--space-4` padding on mobile; step 6 progress bar remains full-width at all sizes.
- **RTL:** Progress bar fills start→end (i.e., right-to-left in Arabic); footer button order mirrors (primary stays at the trailing/forward edge).

### C. Core Commerce Workspace

#### 12. Command Center — `/app/command`
- **Purpose:** Primary dashboard — single-glance business health and priority actions.
- **Layout:** Sidebar + top nav shell. Content: top row date-range filter (end-aligned), KPI row (4 metric cards), 2-column below (start: revenue trend chart card, spanning 2/3; end: "Needs attention" queue card, 1/3), then 3-column row (Recent orders / Active conversations / Opportunity pipeline mini-view), then full-width row (Integration health strip + Automation activity feed), AI recommendations surfaced as a dismissible `--gradient-ai`-bordered card pinned near the top when present.
- **Reused components:** Metric card, Chart, Glass card, Badge, Skeleton, Empty state, Date picker, Quick action buttons (floating group: "New order," "New product," "Send campaign").
- **Actions:** Change date range, Dismiss/act on AI recommendation, Jump to detail (each mini-panel links to its full screen), Trigger quick actions.
- **Data displayed:** Revenue, conversion rate, AOV, active conversations count (KPIs); daily revenue line (chart); pending actions list; AI recommendation text + suggested action; 5 most recent orders; 5 most recent conversations w/ unread state; pipeline stage counts; per-integration status dots; last 5 automation runs.
- **States — L:** each card independently skeletons on load (staggered, not blocking whole page). **E:** brand-new workspace shows a unified "Let's get your first sale" empty state replacing the KPI+chart area with a guided checklist linking to onboarding-incomplete steps. **Er:** any single card that fails to fetch shows its own inline Error state (7.9) without blocking sibling cards. **S:** n/a (dashboard, not a form). **P:** n/a.
- **Desktop/tablet/mobile:** 3-column row → 2-column (tablet) → 1-column stacked (mobile); quick actions collapse into a single floating "+" action button with an expandable menu on mobile.
- **RTL:** Chart x-axis (time) still progresses left→right per data-visualization convention even in RTL (documented exception, Section 11); all surrounding chrome mirrors.

#### 13. Inbox — `/app/inbox`
- **Purpose:** Unified AI + human conversation management across channels.
- **Layout:** Three-column desktop (list 320px / active conversation flexible / context panel 340px); tablet collapses context panel into a slide-over triggered from a header icon; mobile is single-pane with a back-navigation stack (list → conversation → context, pushed as separate views).
- **Sections:** Column 1: search field, channel filter chips (WhatsApp/Messenger/Instagram/All), conversation list items (avatar, name, channel glyph, last message preview, timestamp, unread dot, priority flag). Column 2: header (customer name, channel, AI/manual toggle switch, Assign dropdown, status select [Open/Pending/Resolved]), message thread (8.16 bubble styles), suggested-reply chips above composer, composer (text + attachment icon + send button). Column 3: customer summary (avatar, contact info, tags), linked order summary card, quick notes field, related conversation history links.
- **Reused components:** Text field (search, composer), Badge, Dropdown menu, Conversation messages (8.16), Empty state, Skeleton, Tooltip.
- **Actions:** Search/filter, Select conversation, Toggle AI/manual control, Accept/edit/discard AI suggestion, Send message/attachment, Assign to teammate, Change status, Add note/tag.
- **Data displayed:** Message history, customer profile snippet, order summary, AI suggested replies, unread counts, priority indicators.
- **States — L:** list skeleton (avatar+2-line shimmer rows) on load; thread skeleton (bubble-shaped shimmer) when opening a conversation. **E:** no conversations yet → empty state "When customers message you, they'll show up here" with a "Connect WhatsApp" CTA if unconnected; no conversation selected (desktop) → center illustration "Select a conversation to get started." **Er:** send-failure shows a red "Failed to send — Retry" chip under the message; connection-lost banner (7.14) if channel disconnects mid-session. **S:** sent messages show a delivered/read checkmark progression matching WhatsApp-style semantics. **P:** n/a beyond role-based assign visibility.
- **Desktop/tablet/mobile:** As described above — full 3-pane / 2-pane+slide-over / stacked single-pane with back button.
- **RTL:** Composer send button and message bubble tails mirror to the appropriate edge; channel glyph badge moves to the bubble's mirrored outer corner.

#### 14. Opportunities — `/app/opportunities`
- **Purpose:** Sales pipeline management.
- **Layout:** Top bar: view toggle (Kanban/Table), search, filters, "New opportunity" primary button. Kanban: horizontally scrollable stage columns, each a glass column header (stage name + count + total value) with draggable opportunity cards. Table: standard data table (8.4).
- **Sections:** Stage columns (e.g., New, Qualified, Proposal, Negotiation, Won, Lost), opportunity cards (customer name, value, probability %, assignee avatar, source badge), detail drawer (full opportunity info, activity timeline, linked customer, edit fields), create/edit modal.
- **Reused components:** Tabs (view toggle styled as segmented control), Table, Drawer, Modal, Badge, Avatar, Text field, Select.
- **Actions:** Drag card between stages, Search/filter, Open detail drawer, Create/edit opportunity, Delete opportunity (confirmation dialog).
- **Data displayed:** Opportunity value, probability, stage, assignee, customer, source, created/updated dates, activity log.
- **States — L:** column/table skeletons. **E:** empty stage column shows a dashed drop-zone with "Drag opportunities here" ghost text; zero opportunities overall shows full empty state with "Create your first opportunity." **Er:** drag-drop failure reverts card with a toast "Couldn't move opportunity — try again." **S:** stage-change toast confirmation; create/edit modal closes with success toast "Opportunity created." **P:** n/a.
- **Desktop/tablet/mobile:** Kanban columns narrow with horizontal scroll on tablet; mobile defaults to Table view rendered as stacked cards (8.4 mobile alternative), Kanban available via explicit toggle with single-column-at-a-time swipe navigation.
- **RTL:** Kanban scroll direction mirrors (columns flow start→end i.e. right-to-left); drag handles unaffected.

#### 15. Customers — `/app/customers`
- **Purpose:** Customer database and relationship history.
- **Layout:** Top bar: search, segment filter dropdown, Export button. Full-width data table below.
- **Sections:** Table columns (avatar+name, segment badge, order count, LTV, last interaction, channel/source), customer detail drawer with tabs (Overview/Orders/Conversations/Notes/Tags), timeline component inside Overview tab.
- **Reused components:** Table, Drawer, Tabs, Badge, Export button (icon button), Empty state.
- **Actions:** Search, Filter by segment, Sort columns, Open customer drawer, Add note/tag, Export list.
- **Data displayed:** Customer identity, segment, order count, lifetime value, last interaction date/channel, full timeline of orders/messages/notes.
- **States — L:** table skeleton; drawer skeleton while loading full profile. **E:** zero customers empty state ("Your customers will appear here once they place an order or message you"). **Er:** export-failure toast with Retry. **S:** export success toast with "Download ready" + link. **P:** n/a.
- **Desktop/tablet/mobile:** Table → stacked cards (8.4) below tablet; drawer goes full-screen on mobile.
- **RTL:** Mirrored; timeline entries flow top-to-bottom unchanged (chronology is not a bidi property), icons/text mirror.

#### 16. Products — `/app/products`
- **Purpose:** Product catalog management.
- **Layout:** Top bar: grid/table toggle, search, category filter, status filter, "Import/Sync" button, "New product" primary button. Bulk-action bar appears on selection.
- **Sections:** Grid view (image-forward cards: photo, title, price, stock badge, status badge, platform glyphs) / Table view (compact rows, same fields). Product detail/edit drawer (opens on row/card click, reuses New Product form layout, Section 17).
- **Reused components:** Table, Glass card (grid item), Badge, Drawer, Buttons, Empty state, Skeleton.
- **Actions:** Toggle grid/table, Search/filter, Bulk edit/archive/delete, Import/sync, Open detail drawer, Create new product.
- **Data displayed:** Product image, title, price, stock level, status (Active/Draft/Archived), sales channel platform icons.
- **States — L:** grid/table skeleton. **E:** empty catalog state with "Add your first product" or "Import from Shopify" dual CTA. **Er:** sync-failure card summary ("38 products failed to sync — View errors"). Low-stock is a distinct warning badge (not an error) on affected rows/cards. **S:** import-success toast with count summary. **P:** n/a.
- **Desktop/tablet/mobile:** Grid: 4-col desktop → 2-col tablet → 1-col mobile; table always available as an alternative on all sizes.
- **RTL:** Mirrored; price alignment stays end-edge (trailing) per the reading direction, numerals remain Western Arabic LTR-rendered.

#### 17. New Product — `/app/products/new`
- **Purpose:** Create/edit a product.
- **Layout:** Two-column desktop: main form column (start, ~65%) + sticky sidebar column (end, ~35%) holding Status/Publish, Organization (categories/tags), and Channels. Single column stacked on mobile/tablet, sidebar content moves below main form.
- **Sections:** Name + description (with "Generate with AI" `--gradient-ai` button opening an inline prompt field), Images (multi-upload dropzone with reorderable thumbnail grid), Pricing (price + compare-at), Inventory (quantity, SKU), Variants (repeatable option/value builder), Categories & tags, SEO fields (meta title/description with char counters), Sales channels (checkbox list w/ platform icons), sidebar Status (Draft/Active toggle), Publish/Save draft actions (sticky footer).
- **Reused components:** Text field, Textarea, File upload, Select, Buttons, Badge, Tooltip.
- **Actions:** Fill fields, Generate description via AI, Upload/reorder images, Add variant, Save draft, Publish, Cancel.
- **Data displayed:** Live character counts (SEO fields), AI generation loading/preview inline before accept.
- **States — L:** AI-generate button shows loading state on its own (isolated, doesn't block form); image upload shows per-thumbnail progress. **E:** no images yet shows the dropzone prominently as the only content in that section. **Er:** upload-failure per-thumbnail with retry icon; required-field validation on Publish attempt scrolls to first error. **S:** "Product created" toast + redirect to product detail; "Draft saved" toast (non-navigating) for draft. **P:** n/a.
- **Desktop/tablet/mobile:** As above; variant builder becomes an accordion of variant "cards" on mobile instead of an inline table.
- **RTL:** Mirrored; AI-generate button icon/gradient direction flips with the gradient's angle mirrored (135deg → 45deg equivalent visually) to keep the "flow" reading start-to-end.

#### 18. Orders — `/app/orders`
- **Purpose:** Order management and fulfillment.
- **Layout:** Top: status tabs (All/Pending/Paid/Fulfilled/Refunded/Cancelled) as a segmented control, search + advanced filter button (opens filter popover: date range, channel, payment status). Table below. Detail drawer on row click.
- **Sections:** Table columns (order #, customer, total, channel badge, payment status badge, fulfillment status badge, date). Detail drawer: header (order #, status, risk badge if flagged), timeline (created→paid→fulfilled events), line items table with totals breakdown, customer details card, action row (Fulfill/Refund/Cancel as contextual buttons with confirmation dialogs).
- **Reused components:** Tabs, Table, Drawer, Badge, Confirmation dialog, Alert (fraud/risk warning).
- **Actions:** Filter/search/sort, Open order drawer, Fulfill order, Refund (full/partial), Cancel order.
- **Data displayed:** Order totals, item-level breakdown, customer info, payment/fulfillment states, risk score/flags.
- **States — L:** table + drawer skeletons. **E:** zero orders state ("Orders will show up here once customers start buying"). **Er:** refund/cancel failure toast with Retry; fraud/risk warning rendered as a persistent amber Alert at the top of the drawer, not dismissible until acknowledged. **S:** status-change toast ("Order fulfilled," "Refund issued"). **P:** refund/cancel actions hidden or disabled per role permission with tooltip explaining why.
- **Desktop/tablet/mobile:** Table → stacked cards below tablet; drawer full-screen on mobile with sticky action footer.
- **RTL:** Mirrored; timeline events flow top-to-bottom unchanged, connecting line and icons mirror horizontally where directional.

### D. Marketing and AI

#### 19. Content Studio — `/app/studio`
- **Purpose:** AI-assisted marketing content creation.
- **Layout:** Two-column: form column (start, ~40%) + live preview column (end, ~60%, sticky).
- **Sections:** Form: Platform/channel selector (chips: Instagram/Facebook/WhatsApp Status/etc.), Campaign objective select, Product picker (searchable multi-select with thumbnails), Tone select + Language select, AI prompt textarea, "Generate" primary `--gradient-ai` button. Preview: platform-accurate mock frame (e.g., Instagram post chrome) showing generated caption + media area, Regenerate/Edit controls beneath, media upload/replace control, action row (Save draft / Approve / Publish).
- **Reused components:** Buttons, Select, Textarea, File upload, Glass card, Tabs (if multiple generated variants shown), Alert.
- **Actions:** Configure inputs, Generate content, Regenerate, Manually edit generated caption, Replace media, Save draft, Approve, Publish.
- **Data displayed:** Generated caption text, selected product previews, platform preview mock.
- **States — L:** Generate button loading + preview area shows an AI-thinking shimmer (gradient-ai tinted) while streaming text in. **E:** preview column shows a placeholder "Your generated content will appear here" before first generation. **Er:** generation-failure Alert ("Couldn't generate content — try again") inline above preview; publish-error state shows a persistent Alert with per-platform failure reason ("Instagram: token expired — Reconnect"). **S:** "Draft saved" / "Published" toasts; published state shows a small "Live" badge on the preview frame. **P:** n/a.
- **Desktop/tablet/mobile:** Two-column → stacked (form above preview) on tablet/mobile, preview loses sticky behavior on mobile.
- **RTL:** Mirrored; generated Arabic captions render right-aligned inside the platform mock regardless of the mock platform's own native direction convention (documented as content-language-driven, not shell-driven).

#### 20. Campaign Calendar — `/app/calendar`
- **Purpose:** Schedule and visualize campaign content over time.
- **Layout:** Top bar: view toggle (Month/Week/Agenda), platform/status filter chips, "New campaign" primary button, month navigation (prev/next/today). Calendar grid or agenda list fills remaining space.
- **Sections:** Calendar cells with campaign chips (platform-colored left border, truncated title, status dot), drag-and-drop between days/times, campaign detail drawer (full content preview, schedule time, platform, status history), create campaign modal/drawer.
- **Reused components:** Buttons, Badge, Drawer, Tabs, Date picker (for modal scheduling field).
- **Actions:** Switch views, Filter, Navigate months, Drag-reschedule campaign, Open detail drawer, Create campaign.
- **Data displayed:** Campaign title, platform, scheduled time, status (Draft/Scheduled/Published/Failed).
- **States — L:** calendar grid skeleton (empty cell shimmer). **E:** empty month state ("No campaigns scheduled this month — Create one"). **Er:** failed campaign chips show a red dot + on click, drawer surfaces failure reason with "Retry publish" action; drag-reschedule failure reverts with toast. **S:** reschedule/create success toast. **P:** n/a.
- **Desktop/tablet/mobile:** Month view → Week view auto-suggested on tablet → Agenda (list) view default on mobile with Month/Week available via toggle but denser.
- **RTL:** Calendar week starts per locale convention (Saturday for many Arabic locales, configurable); month grid mirrors so days still flow in natural reading order for the active language.

#### 21. Analytics — `/app/analytics`
- **Purpose:** Business performance reporting.
- **Layout:** Top bar: date-range filter + comparison toggle ("vs previous period"), Export button. KPI row (4 cards), main revenue chart (full-width), 2-column row (Sales by channel donut/bar + Top products list), 2-column row (Customer acquisition chart + AI-assisted conversions metric card), Campaign performance table at bottom.
- **Reused components:** Metric card, Chart, Table, Date picker, Buttons, Skeleton, Empty state.
- **Actions:** Change date range/comparison, Export report, Drill into a chart segment (opens filtered table view).
- **Data displayed:** Revenue, orders, conversion rate, AOV with period-over-period deltas; channel breakdown; top products by revenue/units; new vs returning customer acquisition; conversions attributed to AI conversations; campaign-level performance metrics.
- **States — L:** every chart/card independently skeletons. **E:** insufficient-data state per chart ("Not enough data yet for this period" with a muted placeholder chart shape) rather than a blank card. **Er:** export-failure toast with Retry. **S:** export-ready toast with download link. **P:** advanced/AI-attribution metrics show a locked-feature overlay (7.13) on lower-tier plans.
- **Desktop/tablet/mobile:** 2-column rows stack to 1-column on tablet/mobile; charts remain full-width and horizontally scrollable if data-dense on mobile.
- **RTL:** Chart axes keep LTR time convention (documented exception, Section 11); surrounding labels/legend mirror.

#### 22. Automations — `/app/automations`
- **Purpose:** Build and monitor rule-based/AI automations.
- **Layout:** List view (top bar: search, "Create automation" button, "Browse templates" ghost button) transitioning to a full-screen visual workflow builder canvas when creating/editing.
- **Sections:** List: automation rows (name, enabled toggle, trigger summary, execution count, success rate badge). Builder: node-based canvas (trigger node → condition nodes → action nodes, connected by lines), node library sidebar, node config panel (opens on node click), "Test automation" button (runs a dry-run with sample data), execution history tab (table: timestamp, trigger, outcome, duration), failure detail expandable row (stack-trace-style but merchant-readable reason).
- **Reused components:** Table, Toggle switch, Badge, Buttons, Drawer/panel (node config), Tabs, Empty state, Modal (templates gallery).
- **Actions:** Toggle enabled/disabled, Search, Create from scratch or template, Edit automation (opens builder), Add/connect/configure nodes, Test run, View execution history, Duplicate/delete automation.
- **Data displayed:** Trigger/condition/action configuration, execution count, success rate %, per-run history with outcomes.
- **States — L:** list skeleton; builder canvas shows a loading spinner before nodes render; test-run shows an animated pulse traveling along the node connections while executing. **E:** zero automations state with template gallery prominently offered instead of a bare CTA. **Er:** failed execution rows expand to show a plain-language failure reason ("WhatsApp message failed — customer number invalid") + "Retry" per-row action; builder shows inline validation on incomplete nodes (red outline + tooltip) blocking save. **S:** "Automation saved," "Test run succeeded" toasts; successful test highlights the full node path in green momentarily. **P:** advanced trigger types locked on lower plans (7.13 inline variant on that node option).
- **Desktop/tablet/mobile:** Builder canvas is desktop/tablet-first (pan/zoom); mobile shows a read-only simplified step-list view of any automation with an "Edit on desktop" notice for the full builder.
- **RTL:** Node canvas flow direction mirrors (start→end reads right-to-left), connector arrows flip; canvas pan/zoom controls relocate to the mirrored corner.

#### 23. Agent Settings — `/app/agent-settings`
- **Purpose:** Configure the AI assistant's behavior.
- **Layout:** Two-column: settings form (start, scrollable, grouped into cards) + sticky "Test conversation" panel (end, persistent chat-like preview reflecting live edits).
- **Sections:** Identity card (assistant name, avatar, tone select), Languages card (multi-select checklist), Business instructions (large textarea, "knowledge" style), Escalation rules (repeatable condition builder: "If customer asks about X → escalate to Y"), Working hours (day/time range pickers + after-hours behavior select), Confidence threshold (slider with live description of behavior at current value), Restricted topics (tag input list), Human handoff (toggle + assignee/team select), sticky footer Save/Reset.
- **Reused components:** Text field, Textarea, Select, Toggle, Slider, Tag input, Buttons, Glass card.
- **Actions:** Edit each setting, Send test message in preview panel, Save changes, Reset to defaults (confirmation dialog).
- **Data displayed:** Live-updating test conversation reflecting unsaved changes (labeled "Preview — not saved yet" until Save is pressed).
- **States — L:** test panel shows a typing-indicator bubble while generating a preview reply. **E:** test panel starts with a placeholder prompt suggestion chips ("Try: 'What are your store hours?'"). **Er:** save-failure Alert at top of form, field-level validation for malformed escalation rules. **S:** "Settings saved" toast; Reset requires confirmation dialog (7.10) before reverting. **P:** n/a.
- **Desktop/tablet/mobile:** Two-column → stacked (test panel moves below form, loses sticky) on tablet/mobile, or accessible via a floating "Test" button that opens the preview as a bottom sheet on mobile.
- **RTL:** Mirrored; slider fills start→end; test conversation bubbles use the same mirroring as Inbox (8.16).

### E. Integrations and Administration

#### 24. Integrations — `/app/integrations`
- **Purpose:** Manage third-party platform connections.
- **Layout:** Grid of integration cards (8.15), grouped by category headers (Commerce, Messaging/Social, Payments, AI Provider).
- **Sections:** Cards for Shopify, WooCommerce, Meta/Facebook, Instagram, WhatsApp, Stripe, AI/LLM provider — each per Section 8.15 spec; clicking a card opens a detail modal/drawer with full setup steps, permission scopes list, and error details.
- **Reused components:** Integration card, Badge, Modal/Drawer, Buttons, Alert.
- **Actions:** Connect, Configure, Reconnect, Disconnect (confirmation dialog), View setup steps, View error details.
- **Data displayed:** Connection status, last sync timestamp, granted permissions, error messages/codes.
- **States — L:** card shows a "Syncing…" pulsing badge state during active sync. **E:** n/a (fixed integration list, not user-populated). **Er:** error status badge + expandable "Error details" section with plain-language cause and a "Fix it" action (deep-links to the relevant re-auth step). **S:** "Connected" success toast + badge flips to connected state with a brief highlight animation. **P:** connect/disconnect actions disabled for non-admin roles with explanatory tooltip.
- **Desktop/tablet/mobile:** Grid 3-col → 2-col → 1-col.
- **RTL:** Mirrored; status badge dot position stays leading-edge of the badge text in both directions (i.e., mirrors with the pill).

#### 25. Team — `/app/team`
- **Purpose:** Manage workspace members and roles.
- **Layout:** Top bar: search, "Invite member" primary button. Table below.
- **Sections:** Table (avatar+name, email, role badge, status [Active/Invited/Suspended], last active date, row actions menu), Invite-member dialog (email input w/ chip-add for multiple, role select), Change-role inline dropdown per row, Remove-member confirmation dialog, "You" indicator badge on the current user's row, Owner row shows role as non-editable/protected with a tooltip explaining why.
- **Reused components:** Table, Modal, Dropdown menu, Badge, Confirmation dialog, Buttons.
- **Actions:** Search, Invite member(s), Change role, Resend invitation, Remove member.
- **Data displayed:** Member identity, role, invitation/account status, last active timestamp.
- **States — L:** table skeleton; invite dialog shows per-email sending state. **E:** solo workspace state ("You're the only member — Invite your team"). **Er:** invite-failure inline per malformed/duplicate email chip (red outline + message); remove-failure toast. **S:** "Invitation sent" / "Role updated" / "Member removed" toasts. **P:** invite/role-change/remove actions hidden for non-admin roles; Owner role protected from removal/demotion entirely (control rendered disabled with tooltip, not hidden, so its existence is discoverable).
- **Desktop/tablet/mobile:** Table → stacked cards below tablet.
- **RTL:** Mirrored; row action menu (⋯) sits at the row's leading edge in RTL to match the mirrored table reading order.

#### 26. Billing — `/app/billing`
- **Purpose:** Manage subscription and payment.
- **Layout:** Top: current plan summary card (plan name, price, renewal date, "Change plan" button) + usage meters row (conversations, products, team seats as progress bars with X/Y counts). Below: Plan comparison table (collapsible, opens from "Change plan"), Payment method card, Invoice history table, Danger-zone cancellation link at bottom.
- **Sections:** As above, plus Cancellation flow (multi-step modal: reason select → retention offer screen → final confirmation with typed-confirmation for irreversibility).
- **Reused components:** Glass card, Table, Modal, Buttons, Badge, Alert, Confirmation dialog.
- **Actions:** Upgrade/downgrade plan, Update payment method, Download invoice, Cancel subscription.
- **Data displayed:** Current plan/usage/renewal, payment method (masked card), invoice list with status (Paid/Failed/Refunded), plan comparison feature matrix.
- **States — L:** usage meters and invoice table skeleton on load. **E:** no invoices yet state (new account). **Er:** failed-payment Alert banner persistent at top of page until resolved ("Your last payment failed — Update payment method"), individual failed invoice rows badge red with "Retry payment" action. **S:** "Plan updated," "Payment method updated" toasts; successful payment invoice rows badge green. **P:** billing screen fully hidden/restricted for non-owner roles (redirect with explanatory message), visible read-only for admins per plan's permission model.
- **Desktop/tablet/mobile:** Usage meters row stacks to 2-col then 1-col; plan comparison table becomes swipeable cards on mobile.
- **RTL:** Mirrored; progress bars fill start→end; masked card number stays LTR (numeric convention).

#### 27. Store Settings — `/app/settings`
- **Purpose:** Configure store-level operational settings.
- **Layout:** Start-edge settings sub-navigation (sticky list of section anchors) + end-edge content column, each section a distinct glass card.
- **Sections:** General business info, Store identity (logo/name/description), Currency & timezone, Localization (default language, supported storefront languages), Notifications (channel toggles: email/SMS/push per event type), Order settings (auto-fulfillment rules, order number format), Customer communication (default sender name, reply-to), Data synchronization (sync frequency, conflict resolution rule), Danger zone (delete store — red-bordered card, isolated at the very bottom).
- **Reused components:** Text field, Select, Toggle, Glass card, Buttons, Confirmation dialog (danger zone, typed-confirmation).
- **Actions:** Edit and save each section (independent save-per-card, not one giant form), Delete store (multi-step confirmation).
- **Data displayed:** Current configured values per section.
- **States — L:** per-card skeleton on load; per-card "Saving…" state on its own Save button. **E:** n/a (all fields have defaults). **Er:** per-field validation inline; save-failure Alert scoped to that card only. **S:** per-card "Saved" toast/inline checkmark. **P:** Danger zone actions restricted to Owner role only.
- **Desktop/tablet/mobile:** Sub-nav collapses into a top horizontal scroll tab strip below tablet; single column throughout on mobile.
- **RTL:** Sub-nav moves to the mirrored edge; section anchors still scroll-highlight correctly.

#### 28. Security — `/app/security`
- **Purpose:** Account security management.
- **Layout:** Single column of glass cards, `--space-6` gap.
- **Sections:** Password change card (current/new/confirm fields), Two-factor authentication card (status badge + "Set up" placeholder flow trigger), Active sessions card (list: device/browser icon, location, last active, "This device" tag, per-row "Sign out" action, "Sign out all other sessions" bulk action), Login activity card (table: timestamp, IP/location, device, success/fail badge), Security alerts card (list of flagged events, e.g. "New login from unrecognized device"), Account deletion card (danger-bordered, isolated, requires password + typed confirmation).
- **Reused components:** Text field, Table, Badge, Buttons, Confirmation dialog, Alert.
- **Actions:** Change password, Initiate 2FA setup, Terminate individual/all sessions, Review login activity, Delete account.
- **Data displayed:** Session device/location/timestamp data, login history, security alert descriptions.
- **States — L:** sessions/login-activity tables skeleton. **E:** no security alerts state ("No alerts — your account looks secure," with a calm success-tinted icon rather than empty gray). **Er:** password-change validation (current password incorrect, new password reused); session-termination failure toast. **S:** "Password updated," "Session ended" toasts/confirmations. **P:** n/a beyond standard auth.
- **Desktop/tablet/mobile:** Cards remain single-column at all sizes; tables within cards use the mobile stacked alternative (8.4) below tablet.
- **RTL:** Mirrored; IP/timestamp data stays LTR per convention within an otherwise RTL row.

#### 29. API Keys — `/app/api-keys`
- **Purpose:** Manage programmatic API access.
- **Layout:** Top bar: "Create API key" primary button. Table below. Persistent security notice banner near top.
- **Sections:** Security warning Alert ("API keys grant full account access — store them securely"), Table (key name, masked key preview, permissions badges, last-used date, created date, Revoke row action), Create-key dialog (name field, permission checklist [read/write per resource], "Create" button → one-time secret reveal screen with Copy button and a persistent "You won't be able to see this again" warning), Usage documentation link card at page bottom.
- **Reused components:** Table, Modal, Alert, Badge, Buttons, Confirmation dialog (revoke).
- **Actions:** Create key, Copy secret (one-time), Revoke key.
- **Data displayed:** Key metadata (name, masked value, permissions, last used, created date).
- **States — L:** table skeleton; key-creation shows a brief generating spinner before reveal screen. **E:** zero keys state ("No API keys yet — Create one to start integrating"). **Er:** revoke-failure toast with Retry. **S:** "Copied to clipboard" inline confirmation on the copy button (icon swaps to checkmark for 2s); "Key revoked" toast. **P:** creation/revoke restricted to admin/owner roles.
- **Desktop/tablet/mobile:** Table → stacked cards below tablet; one-time secret reveal remains a full modal at all sizes (never inline) to keep the "copy now, dismiss forever" moment unambiguous.
- **RTL:** Mirrored; the secret string itself renders LTR always (it's an opaque token, not language content), with `dir="ltr"` explicitly set inside an RTL page.

#### 30. Privacy — `/app/privacy`
- **Purpose:** Merchant-facing privacy/data controls.
- **Layout:** Single column, grouped glass cards, similar rhythm to Store Settings.
- **Sections:** Data collection explanation card (plain-language summary + link to full policy), Data export request card (button + status of last request: Not requested / Preparing / Ready-to-download / Expired), Data deletion request card (explains scope + irreversible warning + request button with confirmation dialog), Marketing preferences (toggle list: product updates, tips, partner offers), Consent history table (what was consented to, when, version), Legal privacy content (collapsed accordion or link to `/privacy-policy` full text, following the same layout pattern as Terms, Section 8).
- **Reused components:** Glass card, Toggle, Table, Buttons, Confirmation dialog, Badge (request status).
- **Actions:** Request data export, Request data deletion, Toggle marketing preferences, Review consent history, Download export when ready.
- **Data displayed:** Export/deletion request status, consent history entries, current preference toggle states.
- **States — L:** export status badge shows "Preparing…" with a subtle progress pulse. **E:** empty consent history for brand-new accounts (rare, but handled with a simple note). **Er:** export-request failure toast; deletion request requires explicit typed confirmation given irreversibility. **S:** "Export ready" notification (also surfaces in the top-nav Notification Menu) with Download button; "Preferences saved" toast. **P:** n/a.
- **Desktop/tablet/mobile:** Standard single-column card stack, no structural change needed across breakpoints beyond padding.
- **RTL:** Mirrored throughout.

#### 31. Operator Console — `/app/operator`
- **Purpose:** Platform-admin oversight across all tenant workspaces (Anthropic-style "God mode," used internally only).
- **Layout:** Distinct visual treatment from the merchant app — same design language but with a persistent amber-tinted top banner reading "Privileged access — actions here affect live customer workspaces," reinforcing this is not a normal screen. Sidebar collapses to a simplified operator-only nav (Tenants, Platform Health, Jobs, Security, Audit Log).
- **Sections:** Tenant/store list (searchable table: workspace name, plan, MRR, status [Active/Trial/Suspended/Churned], created date), Platform health metrics row (uptime, API latency, error rate KPI cards), Background jobs panel (queue name, pending/processing/failed counts, per-job drill-down), Integration failures feed (cross-tenant, filterable by integration type), Security events feed (cross-tenant flagged events), Tenant detail drawer (full tenant profile: plan/billing summary, usage, support notes, impersonate-for-support action gated by its own confirmation + audit entry), Audit log (immutable table: actor, action, target, timestamp — filterable, exportable), Support actions (e.g., "Extend trial," "Issue credit," "Suspend workspace" — each behind its own confirmation dialog).
- **Reused components:** Table, Metric card, Drawer, Badge, Confirmation dialog, Alert, Buttons — all restyled with the amber privileged-access accent replacing blue as the dominant chrome color for this section only, to make it unmistakably distinct at a glance.
- **Actions:** Search/filter tenants, Drill into tenant, Impersonate for support (double confirmation), Manage jobs (retry/cancel), Review security/integration events, Query audit log, Execute support actions.
- **Data displayed:** Cross-tenant operational, billing, and security data; system health metrics; immutable audit trail.
- **States — L:** metrics/tables skeleton. **E:** empty job queue state ("No background jobs pending — all clear," success-tinted). **Er:** platform-health cards flip to danger styling when thresholds are breached (e.g., error rate card turns red-bordered with a pulsing alert glyph); failed-job rows expand with stack-trace-style detail (developer-readable here, unlike merchant-facing plain-language errors). **S:** support-action toasts explicitly note the audit entry created ("Trial extended — logged to audit trail"). **P:** entire route returns a 404-style "Not found" (not a 403) to any non-operator role, to avoid revealing the route's existence; within the console, any operator role tier without a specific permission sees actions disabled with a tooltip.
- **Desktop/tablet/mobile:** Desktop/tablet-first tool (operators are assumed to be at a desk); mobile renders a read-only simplified view (health metrics + audit log only) with a notice that management actions require desktop.
- **RTL:** Fully supported per the same rules as the rest of the app, though operator staff usage is expected to be predominantly LTR internally — RTL is not deprioritized, just less frequently exercised.

---

## 10. Desktop / Tablet / Mobile Behavior — Global Rules

- **Desktop (≥1200px):** Full three-tier shell (sidebar + top nav + content), multi-column layouts, hover states fully active, drawers slide in at fixed width leaving content visible/dimmed behind.
- **Tablet (768–1199px):** Sidebar auto-collapses to a 72px icon rail by default (user can pin it open, persisted preference); three-column screens (Inbox) degrade to two-pane + slide-over; data-dense grids drop to 2 columns; drawers still slide in but widen to ~60% of viewport.
- **Mobile (<768px):** No persistent sidebar — hamburger-triggered drawer only; top nav condenses to hamburger + page title + essential icons (search, notifications, avatar — overflow into a "More" menu if needed); all drawers/modals go full-screen; tables convert to stacked cards (8.4); multi-column dashboards stack to single column in a fixed priority order (KPIs → primary chart → secondary content); floating action button pattern replaces some toolbar button clusters (e.g., Command Center quick actions, Products "New product").
- **Touch targets:** Minimum 44×44px on tablet/mobile regardless of the visual glyph size.
- **Sticky elements:** Only one sticky element stacks at a time on mobile (top nav OR a form footer, never both competing) — modal/drawer footers take priority over page-level stickiness while open.

---

## 11. Arabic RTL and English LTR Behavior

- **Global mirroring:** All layout uses logical CSS properties (`margin-inline-start`, `padding-inline-end`, `inset-inline-start`, etc.) — never physical `left`/`right` — so `dir="rtl"` on the root flips the entire shell (sidebar, nav clusters, drawers, chevrons, form field icon positions) automatically.
- **Iconography:** Directional icons (arrows, chevrons, "back," send-message paper-plane, undo/redo) flip horizontally in RTL. Non-directional icons (bell, gear, search magnifier, trash) do not flip.
- **Documented exceptions (do not mirror):** (1) Chart time-axes and line/bar chart data flow always progress left→right regardless of UI direction, per data-visualization convention — axis *labels and legends* around the chart still mirror. (2) Numerals render as Western Arabic digits left-to-right even inside RTL sentences (standard bidi digit behavior). (3) Opaque tokens (API keys, order IDs, reference IDs, masked card numbers) are wrapped in `dir="ltr"` spans within RTL context. (4) Code/monospace blocks (webhook payloads, JSON) stay LTR.
- **Typography pairing:** Manrope (Latin) + IBM Plex Sans Arabic run side-by-side in mixed-language content (e.g., a customer name in Arabic next to an English order ID) without a visible size/weight mismatch — both tuned to the same cap-height ratio.
- **Text expansion:** Arabic UI strings can run 15–25% longer than English equivalents; all buttons/badges/nav labels use flexible (not fixed) widths, and truncation with an ellipsis + tooltip is the fallback for genuinely fixed-width contexts (table cell headers, badge pills).
- **Forms:** Label-above-field pattern is direction-agnostic by design specifically to avoid the harder problem of mirroring label-beside-field layouts.
- **Date/time/currency:** Localized per the user's chosen language/region setting independent of UI direction (a French-Canadian merchant using the Arabic UI still sees their configured currency format) — language (content) and locale (formatting) are separate settings.

---

## 12. Accessibility Rules

- **Contrast:** All body text ≥4.5:1, large text (≥24px or 19px bold) and meaningful icons ≥3:1, verified against actual glass-over-background composite color (not the flat token alone) since blur/transparency can shift effective contrast — glass surfaces are calibrated with this composite in mind (Section 2 hexes already account for it against `--color-bg-base`).
- **Focus:** Every interactive element has a visible `--glow-focus` ring; focus order follows visual/DOM order; no focus traps outside intentional modal/drawer contexts (which trap correctly and return focus to the trigger on close).
- **Color independence:** Status is never conveyed by color alone — every colored state (badges, deltas, form validation) pairs with an icon/glyph and/or text label.
- **Motion:** All shimmer/pulse/slide animations respect `prefers-reduced-motion: reduce` by swapping to instant-state changes or simple opacity crossfades ≤150ms.
- **Keyboard:** Full app operable via keyboard — Command Palette, Kanban drag-and-drop (with a keyboard-accessible "Move to stage" menu fallback), Calendar drag-reschedule (keyboard fallback via detail drawer's schedule field), node-based Automation builder (keyboard fallback via a structured "Add step" list view alternative to the canvas).
- **Screen readers:** Charts include a "View as table" text alternative (8.13); toasts announce via `aria-live="polite"`; destructive confirmation dialogs announce via `aria-live="assertive"`; skeleton loaders are marked `aria-busy="true"` with an `aria-label` describing what's loading.
- **Touch/zoom:** Layout tolerates 200% browser zoom without horizontal scroll loss of function; pinch-zoom never disabled.
- **Language attribute:** `<html lang>` and `dir` update together on language switch, so assistive tech pronunciation and layout direction stay in sync.

---

## 13. Icon System

- **Style:** Single 1.5px stroke-weight line icons (no filled icons except status dots and small functional glyphs like checkmarks), 20px/24px grid, rounded joins/caps to match the 14–24px corner-radius language of the rest of the UI.
- **Source:** A single consistent icon set throughout (e.g., Phosphor or Lucide-equivalent stroke family) — never mixing icon styles from multiple libraries.
- **Sizing tokens:** `--icon-sm` 16px (inline with `--text-body-sm`), `--icon-md` 20px (default, nav/buttons), `--icon-lg` 24px (empty-state headers, card headers), `--icon-xl` 64px (full-page empty/error illustrations, built from the same line-icon language rather than a different illustration style).
- **Color:** Icons inherit `currentColor` by default (matching adjacent text), except semantic-status icons which take their fixed semantic color (success/warning/danger/info/AI-gradient) regardless of surrounding text color.
- **AI marker icon:** A consistent small sparkle/spark glyph in `--gradient-ai` denotes anything AI-generated or AI-suggested across Inbox, Studio, Automations, and Command Center recommendations — this is the one icon allowed to carry a gradient fill rather than flat currentColor.

---

## 14. Animation & Transition Rules

| Interaction | Duration | Easing |
|---|---|---|
| Hover state changes (buttons, cards, rows) | 120ms | ease-out |
| Focus ring appearance | 100ms | ease-out |
| Modal/drawer open | 220ms | cubic-bezier(0.16,1,0.3,1) (soft overshoot-free spring) |
| Modal/drawer close | 160ms | ease-in |
| Toast enter/exit | 200ms enter / 150ms exit | ease-out / ease-in |
| Tab underline slide | 180ms | ease-in-out |
| Skeleton shimmer sweep | 1400ms loop | ease-in-out |
| Page/route transition | 150ms crossfade | ease |
| Kanban card drag | follows pointer 1:1, drop settles in 180ms | spring |
| AI "thinking" pulse (Studio/Inbox) | 1200ms loop | ease-in-out |

Rules: motion always communicates state change, never plays for decoration alone; one orchestrated moment per screen at most (e.g., onboarding step-6 sync progress) rather than scattered ambient effects; every duration above collapses to ≤1 frame changes under `prefers-reduced-motion`.

---

## 15. Empty / Loading / Error / Locked States — Summary Matrix

Full per-screen detail lives in Section 9; this is the cross-cutting pattern reference.

| State | Visual pattern | Copy pattern |
|---|---|---|
| **Empty** | Line icon (64px) + `--text-h3` headline + one supporting sentence + optional primary CTA | "[Thing] will show up here [when X happens]" or "Create your first [thing]" |
| **Loading** | Shape-matched skeleton (7.7) or inline spinner for isolated actions | No copy needed for skeletons; buttons swap label for spinner |
| **Error (inline)** | Danger-colored icon + short message + Retry text action | "[Action] failed — [why, if known]" |
| **Error (full panel)** | Icon + `--text-h3` + Retry primary + secondary escape action | "Something needs your attention" pattern, screen-specific detail |
| **Locked/paywall** | Frosted overlay + lock badge (`--gradient-ai`) + plan requirement + Upgrade CTA | "[Feature] is available on the [Plan] plan" |
| **Permission-restricted** | Element disabled + tooltip explaining requirement, OR route-level redirect for fully restricted screens | "You don't have permission to [action] — ask a [role] on your team" |

---

## 16. Asset List

- **Icon set:** Full line-icon library (sidebar nav ×18, top nav ×5, component-level ×~60 covering all actions across 31 screens).
- **Illustrations:** 404 abstract glass-shard illustration, 500 error glyph illustration, empty-state line illustrations (reused base icon at 64px, no separate illustration set needed beyond icons per the restrained direction).
- **Logo:** Primary lockup (full color, for light backgrounds), reversed lockup (white, for dark/glass surfaces), icon-only mark (favicon, collapsed sidebar, workspace switcher).
- **Fonts:** Manrope (weights 400/500/600/700), IBM Plex Sans Arabic (weights 400/500/600/700), JetBrains Mono (weights 400/500).
- **Third-party integration logos:** Shopify, WooCommerce, Meta, Facebook, Instagram, WhatsApp, Stripe — official brand marks placed on neutral white/light tiles inside integration cards for contrast and brand-guideline safety, regardless of app theme.
- **Platform preview mocks (Content Studio):** Frame chrome references for Instagram post/story, Facebook post, WhatsApp message bubble.
- **Landing page assets:** Hero product-preview mock (built from real component library, not a separate static image), integration logo strip (subset of above), trust/security badge row (generic shield/lock iconography, not third-party certification logos unless actually certified).

---

## 17. Developer Handoff Notes

- **Tokens as CSS custom properties:** All Section 2–6 tokens ship as CSS variables on `:root` (dark) and `[data-theme="light"]` (light override block), never hardcoded hex values in component code.
- **Logical properties only:** No `left`/`right`/`margin-left` etc. in component CSS — `inline-start`/`inline-end` throughout, verified by linting against a physical-property blocklist.
- **Glass performance:** `backdrop-filter` is expensive at scale — cap simultaneous blurred surfaces visible in viewport (e.g., don't blur every table row, only container-level surfaces); provide a `prefers-reduced-transparency` fallback that swaps blur for a solid `--color-bg-elevated` fill.
- **Component library:** Build as a shared package (buttons, inputs, cards, table, drawer, modal, toast, badge, tabs, tooltip, dropdown, pagination, date picker, chart wrapper, integration card, conversation bubble, command palette, locked-feature card, confirmation dialog) consumed identically across all 31 screens — no screen-local reimplementations of these primitives.
- **State machine consistency:** Every async list/detail view implements the same four-state contract (`loading | empty | error | ready`) via a shared hook/pattern so skeleton/empty/error components are swapped in consistently rather than ad hoc per screen.
- **RTL testing:** Every component ships a Storybook (or equivalent) entry rendered in both `dir="ltr"` and `dir="rtl"` before merge; automated visual regression runs both directions.
- **Permission gating:** Role checks live in a single shared permissions utility (`can(action, role)`) consumed by both the disabled-state UI and the route guards, so a permission change updates both surfaces from one source of truth.
- **Chart library:** Wrap the chosen charting library (e.g., Recharts/Visx) behind the internal `<Chart>` component described in 8.13 so token-driven theming stays centralized and the RTL axis exception (Section 11) is implemented once.
- **Content/copy source:** All interface strings (including empty/error/toast copy) live in a single i18n resource keyed by string ID, EN and AR maintained as parallel files — no inline hardcoded strings in components, so future languages are additive.

---

## 18. Route-to-Screen Mapping

| Route | Screen |
|---|---|
| `/` | Landing Page |
| `/login` | Login |
| `/signup` | Signup |
| `/verify-email` | Verify Email |
| `/forgot-password` | Forgot Password |
| `/reset-password` | Reset Password |
| `/accept-invite` | Accept Team Invitation |
| `/terms` | Terms and Conditions |
| `/404` (catch-all) | 404 Page |
| `/500` | 500 Page |
| `/app/onboarding` | Onboarding Wizard |
| `/app/command` | Command Center |
| `/app/inbox` | Inbox |
| `/app/opportunities` | Opportunities |
| `/app/customers` | Customers |
| `/app/products` | Products |
| `/app/products/new` | New Product |
| `/app/orders` | Orders |
| `/app/studio` | Content Studio |
| `/app/calendar` | Campaign Calendar |
| `/app/analytics` | Analytics |
| `/app/automations` | Automations |
| `/app/agent-settings` | Agent Settings |
| `/app/integrations` | Integrations |
| `/app/team` | Team |
| `/app/billing` | Billing |
| `/app/settings` | Store Settings |
| `/app/security` | Security |
| `/app/api-keys` | API Keys |
| `/app/privacy` | Privacy |
| `/app/operator` | Operator Console (operator role only) |

*End of design.md*
