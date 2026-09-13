# Frontend Engineering

## Stack and entry points

The canonical frontend is `web/`; there is no second production frontend.

| Concern           | Technology or file                                                     |
| ----------------- | ---------------------------------------------------------------------- |
| UI runtime        | React 19.2.8 and React DOM 19.2.8                                      |
| Language          | TypeScript 5.9.3 in strict project configuration                       |
| Build/dev server  | Vite 8.1.5 with `@vitejs/plugin-react`                                 |
| Routing           | React Router 8.3.0                                                     |
| Motion            | Framer Motion 12                                                       |
| Icons             | Phosphor React and official brand marks through `components/icons.tsx` |
| Tests             | Vitest 4, Testing Library, JSDOM, V8 coverage                          |
| Browser checks    | Playwright Core and the `verify-ui.mjs` scenario                       |
| Formatting/lint   | ESLint 10, TypeScript ESLint, Prettier 3, logical-CSS checker          |
| Entry point       | `web/src/main.tsx`                                                     |
| Route composition | `web/src/app/App.tsx`                                                  |
| Auth state        | `web/src/app/AuthContext.tsx`                                          |
| App chrome        | `web/src/app/AppShell.tsx`                                             |
| API boundary      | `web/src/lib/api.ts` and `web/src/lib/types.ts`                        |

Routes are lazy loaded, which keeps the initial bundle smaller and isolates feature code. A
single `Suspense` loader provides route-loading feedback. `AppErrorBoundary.tsx` catches
unexpected rendering errors and the `/500` route gives users an intentional recovery screen.

## Route model

### Public and identity routes

| Route                 | Screen                                         |
| --------------------- | ---------------------------------------------- |
| `/`                   | Marketing landing page and product explanation |
| `/login`              | Login and optional MFA challenge               |
| `/signup`             | Account and initial workspace registration     |
| `/verify-email`       | Email token verification                       |
| `/forgot-password`    | Password reset request                         |
| `/reset-password`     | Token-based new password                       |
| `/accept-invite`      | Team invitation acceptance                     |
| `/terms`              | Terms and conditions                           |
| `/500`                | General error recovery                         |
| unmatched public path | Branded 404 page                               |

### Authenticated workspace routes

| Route                 | Responsibility                                                     |
| --------------------- | ------------------------------------------------------------------ |
| `/app/command`        | API-backed replies, content decisions, channel setup, and outcomes |
| `/app/inbox`          | Conversation list, detail, notes, replies, suggestions, and media  |
| `/app/opportunities`  | Opportunity pipeline/table, scan, decisions, and attribution       |
| `/app/customers`      | Search/filter, intelligence, segments, timelines, and export       |
| `/app/products`       | Catalog grid/table, filters, state, and product actions            |
| `/app/products/new`   | Product onboarding and image-assisted enrichment                   |
| `/app/orders`         | Order list/detail, totals, status transitions, and checkout action |
| `/app/studio`         | Brand-aware content generation, versions, approval, and publishing |
| `/app/calendar`       | Campaign calendar views and scheduled content                      |
| `/app/analytics`      | Revenue, channel, content, agent, and AI measurements              |
| `/app/automations`    | Definitions, templates, enable/disable, and run history            |
| `/app/integrations`   | Meta, WhatsApp, Shopify, WooCommerce, website, and provider health |
| `/app/agent-settings` | Assistant behavior and store-agent settings                        |
| `/app/team`           | Membership, invites, roles, and revocation                         |
| `/app/billing`        | Entitlement, plans, usage, and billing capability state            |
| `/app/settings`       | Store profile and operational settings                             |
| `/app/security`       | Password, sessions, and MFA management                             |
| `/app/api-keys`       | Scoped website integration keys                                    |
| `/app/onboarding`     | Store activation checklist                                         |
| `/app/privacy`        | Export, retention, and deletion controls                           |
| `/app/operator`       | Protected cross-store operator console                             |

`ProtectedRoute` requires a valid session. `EntitledRoute` checks server-provided feature
entitlements rather than hiding a link only in the browser. `OperatorRoute` requires operator
authorization. `/app/dashboard` is retained as a redirect to `/app/command` for compatibility.

## Application shell

`AppShell.tsx` supplies shared operational navigation:

- Six-link P0 desktop navigation with secondary modules in an accessible disclosure, responsive
  rail, and complete mobile drawer.
- Sticky header with current route context.
- Global command palette for navigation and actions.
- Profile actions; notification claims remain absent until a real event source exists.
- Arabic/English locale switch.
- Dark, light, and system theme selection.
- Mobile bottom navigation for Home, Inbox, Content, Products, and More.
- Entitlement-aware and operator-aware navigation visibility.

The shell uses semantic navigation regions, accessible names, focus management, and shared icon
components rather than emoji, handcrafted SVG approximations, or duplicated page chrome.

## Component organization

```text
web/src/
  app/                 providers, router, guards, shell, error boundary
  components/ui/       buttons, surfaces, feedback, and data-display primitives
  components/layout/   branding and authentication layout
  components/domain/   domain-specific shared presentation
  features/            one folder per route/capability
  i18n/                Arabic/English dictionaries and direction context
  lib/                 API client, shared types, and formatting
  styles/              tokens, global rules, shell, commerce, operations, public pages
```

Shared primitives cover buttons, cards/surfaces, badges, alerts, skeletons, empty states,
tables, segmented controls, progress indicators, pipelines, menus, and feedback. Feature pages
compose these primitives but retain their own business-specific state and API calls.

The catalog defaults to a dense table with labelled mobile rows. Query parameters retain filters
and identify the selected product. `ProductDetail.tsx` uses the strict update contract, omits
provider-owned fields, preserves failed edits, and separates review from activation.
`npm --prefix web run verify:catalog` verifies this flow against the isolated demo API.
Inbox requests reject stale responses; the context rail labels recent-order scope and uses each
order's currency. These local results do not establish provider or production acceptance.

## State and data flow

There is no unnecessary global state library. The frontend uses:

- `AuthContext` for authenticated identity, current store, membership, CSRF token, and refresh.
- `ThemeContext` for dark/light/system preference and document theme state.
- The i18n context for language, dictionary selection, `lang`, and `dir`.
- Local React state for view filters, forms, selections, loading, and transient UI.
- The typed API module for all server state.

The API client sends cookie credentials, serializes JSON when appropriate, attaches the current
CSRF token to state-changing authenticated calls, handles typed results, and converts the
backend error envelope into a frontend error. It does not store authoritative prices, roles,
quotas, approval status, or payment truth in local storage.

## Design system

The visual source is `design.md`, implemented through project-owned tokens.

| Area                                      | Source                                       |
| ----------------------------------------- | -------------------------------------------- |
| Color, spacing, typography, radius, focus | `styles/tokens.css`                          |
| Global resets and accessibility           | `styles/base.css`, `styles/globals.css`      |
| Shell and administrative surfaces         | `styles/admin.css`                           |
| Catalog/order/customer layouts            | `styles/commerce.css`                        |
| Inbox/opportunity/automation layouts      | `styles/operations.css`                      |
| Legal/error/landing surfaces              | `styles/public-pages.css` and feature styles |

The default appearance is a deep graphite dark workspace with restrained blue-violet accents,
translucent layered surfaces, strong information hierarchy, and compact operational density.
Light mode is the same system with alternate tokens, not a separate implementation.

Fonts are bundled locally: Manrope for Latin UI, IBM Plex Sans Arabic for Arabic, and JetBrains
Mono for machine-like values. This avoids runtime font-provider dependence.

## RTL, responsiveness, and accessibility

- Arabic and English use the same component tree.
- The locale context changes `document.documentElement.lang` and `dir`.
- CSS uses logical properties. `scripts/check-logical-css.mjs` rejects disallowed physical
  left/right layout declarations during lint.
- Verification targets are desktop 1440×900, tablet 768×1024, and mobile 390×844.
- Sidebar, tables, filters, cards, master/detail pages, dialogs, and form actions reflow instead
  of creating horizontal page overflow.
- Focus indicators, accessible names, semantic headings, list/navigation roles, keyboard
  behavior, reduced motion, and reduced transparency are part of the release contract.
- The most recent local Axe pass reported zero WCAG violations; gradient surfaces still require
  human contrast review because automated tools cannot always calculate their background.

## Frontend quality gates

| Command                              | Purpose                                                      |
| ------------------------------------ | ------------------------------------------------------------ |
| `npm --prefix web run lint`          | ESLint plus bidirectional logical-CSS enforcement            |
| `npm --prefix web run format:check`  | Prettier verification                                        |
| `npm --prefix web test`              | Vitest component/context/API behavior                        |
| `npm --prefix web run test:coverage` | V8 coverage and configured threshold                         |
| `npm --prefix web run build`         | TypeScript project build and optimized Vite bundle           |
| `npm --prefix web run verify:journeys` | Store/brand profile persistence, grounded reply, and approval-gated publication through the real UI and worker |
| `npm --prefix web run verify:ui`       | Authenticated desktop/tablet/mobile route and browser checks |

Do not copy a historical test count or coverage percentage into a current release claim. Run the
commands above against the candidate and retain their dated output. The optimized build transforms
and code-splits route modules; generated `dist/` and `coverage/` are deliberately excluded from the
handoff archive.
