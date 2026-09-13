# Canonical frontend migration plan

Last updated: 2026-08-08

Status: completed locally and covered by the release candidate verification gates.

## Constraints

- Keep `web/` as the single deployable application.
- Preserve the current API client, cookie session, CSRF contract, server RBAC, store scope,
  feature checks, quotas, idempotency keys, and provider truth.
- Do not add Bootstrap, jQuery, a second router, a global state library, or donor mock data.
- Translate only unencumbered design principles from the static donor.
- Keep changes reversible by vertical slice and run focused tests after every slice.

## Stage 1 — Truth and access policy

1. Add explicit `FREE_ACCESS_MODE` configuration.
2. Make free access server-authoritative: an internal Growth subscription is active without
   a trial expiry while the flag is enabled.
3. Preserve plan quotas, feature checks, RBAC, tenant filters, and audit behavior.
4. Return free-access status from billing capabilities.
5. Reject SaaS plan changes and portal/checkout creation in free mode.
6. Redirect the public billing route to a truthful access/usage view and remove it from
   navigation.
7. Add tests proving no checkout, retained roles/store scope/quotas, and no payment-success
   claim.

## Stage 2 — Foundation and shell

1. Implement the approved dark-first Liquid Glass token model from `design.md` with
   a light secondary mode and project-owned blue-violet accents.
2. Split shared primitives into `components/ui`, layout into `components/layout`, and
   domain-only presentation into `components/domain` without changing API behavior.
3. Rebuild the app shell with:
   - concise primary navigation;
   - collapsible secondary management section;
   - compact top bar with workspace context, free-access status, theme, locale, and account;
   - mobile drawer/bottom actions that retain all critical routes;
   - visible focus and reduced-motion behavior.
4. Lazy-load route modules to reduce initial JavaScript.

## Stage 3 — Entry, authentication, and setup

1. Replace the public hard-coded dashboard and pricing with a truthful product explanation:
   Connect → Operate → Recover revenue.
2. State clearly that launch access requires no card and that external provider actions need
   credentials.
3. Restyle login/account pages while retaining secure form semantics.
4. Surface real onboarding progress and resume links from server state.

## Stage 4 — Core operational routes

Migrate without changing domain behavior:

1. Command Center.
2. Products and product onboarding.
3. Inbox and grounded reply assist.
4. Orders and COD.
5. Opportunities.

Each route receives restrained cards/tables, one clear primary action, truthful empty/error
states, responsive table behavior, and stable semantic status badges.

## Stage 5 — Growth and management routes

1. Content Studio and campaign calendar.
2. Automations with worker/run truth.
3. Analytics with a defined range and server-derived metric descriptions.
4. Integrations with standardized configured/needs action/error/Demo states.
5. Customers, team, settings, security, privacy, API/website, and operator.

## Stage 6 — Donor and legacy cleanup

1. Confirm no production import or route references the donor.
2. Remove the static donor and its archive after the translated tokens are documented.
3. Remove legacy visual-only CSS, hard-coded public metrics, pricing UI, and unreachable
   duplicate route content.
4. Keep dormant Stripe code, migrations, webhook verification, and provider tests intact.

## Stage 7 — Verification

Run:

- Ruff check and formatting check.
- Strict mypy.
- Full pytest suite.
- Frontend lint, Vitest, and production build after a clean install.
- Remote PostgreSQL clean/upgrade migration gate.
- Release secret and binary scan.
- Browser acceptance on 390×844, 768×1024, and 1440×900 in Arabic RTL and English LTR.
- Login, every reachable authenticated route, no unexpected console/page/network errors,
  no broken navigation, and no horizontal overflow.
- Production health/readiness and authenticated journey when deployment credentials are
  reconciled.

## Rollback boundaries

- Access policy is isolated behind configuration and can be disabled without removing
  billing tables or Stripe providers.
- Visual foundation changes do not alter request contracts.
- Route migrations retain the existing feature module boundaries.
- Provider adapters and webhook routes are not rewritten for visual work.

## Completion checkpoint

Stages 1–6 are complete in source:

- free access is server-authoritative and checkout-safe;
- the final shell, tokens, route lazy loading, mobile drawer, and primary/management
  navigation are active;
- public/auth/core/management routes use the canonical visual system;
- real order creation is wired through the existing server contract;
- demo/free/provider truth is visible;
- the donor directory/archive and duplicate overview/sales UI routes are removed.

Stage 7 evidence is recorded in the implementation status and final report after each
release run.
