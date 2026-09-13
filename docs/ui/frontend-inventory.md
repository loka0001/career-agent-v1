# Frontend inventory

Last audited: 2026-08-08

## Decision

`web/` is the only canonical end-user frontend. It already owns routing, authenticated
session lifecycle, CSRF-aware requests, entitlement-aware route guards, localization,
and every application API integration.

The supplied `pillowmart-master-frontend-template/` was a static Colorlib storefront
donor. It was not
an application candidate: it has no package manifest, API client, session model, router,
type contracts, tests, or RTL support. Its shopping cart and checkout pages also conflict
with the current no-payment product phase.

The donor is used only as a visual reference for:

- warm off-white commerce surfaces;
- the restrained plum accent family;
- generous product-led spacing;
- simple bordered buttons and quiet section separation.

No donor HTML, jQuery, Bootstrap runtime, checkout flow, copyrighted logo, font file, or
image asset was copied into the canonical application. The donor readme required Colorlib
copyright preservation or a purchased license, so reusing its shipped assets would have
added an unnecessary licensing and deployment dependency. The donor directory and ZIP
were removed after this inventory and the project-owned token translation were complete.

## Functional frontend — `web/`

| Area        | Inventory                                                                                                                         |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Stack       | React 19.2.8, React DOM 19.2.8, React Router 8.3.0, Vite 8.1.5, TypeScript 5.9.3                                                  |
| Styling     | Dark-first Liquid Glass tokens and authored CSS in `web/src/styles`, with `globals.css` as the import root; no Tailwind or shadcn |
| Motion      | Framer Motion 12.42.2, loaded as a separate Vite chunk                                                                            |
| Data access | Typed fetch wrapper in `web/src/lib/api.ts`, cookie session, CSRF header for mutations                                            |
| Auth        | `AuthContext`, protected routes, operator guard, server-derived subscription state                                                |
| i18n        | Arabic RTL and English LTR context with document `lang` and `dir` updates                                                         |
| Tests       | Vitest component/API tests plus Playwright smoke scripts                                                                          |
| Build       | TypeScript project build followed by Vite production build                                                                        |

### Functional sources worth preserving

- `web/src/lib/api.ts` and `web/src/lib/types.ts`: real request/response contracts.
- `web/src/app/AuthContext.tsx` and `ProtectedRoute.tsx`: session and server entitlement
  boundaries.
- `web/src/features/**`: domain journeys and API mutation logic.
- `web/src/components/icons.tsx`: the single Phosphor icon facade used by product code.
- `web/scripts/verify-ui.mjs` and `verify-production.mjs`: browser error and overflow gates.

### Replaced or reorganized visual sources

- High-contrast glass/aurora surfaces now resolve to opaque warm-neutral operational
  surfaces.
- The dense sidebar is now primary operations plus a management group; billing is absent.
- Hard-coded landing metrics/pricing were replaced by a truthful capability workflow.
- Shared components are grouped by UI, layout, and domain responsibility, with a
  compatibility export retained for existing imports.
- Route headings and core actions respond to the persisted Arabic RTL / English LTR locale.

## Removed donor frontend — inventory at removal

| Area          | Inventory                                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| Stack         | Static HTML, Bootstrap CSS, jQuery 1.12, vendor carousel/lightbox scripts, Sass source                        |
| Routes        | Storefront home, catalog, product detail, cart, checkout, confirmation, login, blog, contact                  |
| Design tokens | Plum `#B08EAD`, ink `#4B3049`, off-white and pale blue surfaces                                               |
| Assets        | Storefront product photography, vendor webfonts, template logo and documentation                              |
| Reusable code | None copied directly; only palette/rhythm principles are translated into new project-owned tokens             |
| Licensing     | Colorlib notice requires attribution or a purchased license; shipped assets stay out of the production bundle |

## Compatibility and conflict assessment

| Concern        | `web/`                                     | Donor                     | Resolution                                                        |
| -------------- | ------------------------------------------ | ------------------------- | ----------------------------------------------------------------- |
| Router         | React Router SPA                           | Static links              | Preserve React Router                                             |
| TypeScript     | Strict TypeScript                          | None                      | Preserve strict contracts                                         |
| Styling        | Project tokens/CSS                         | Bootstrap + Sass          | Translate principles into project tokens; do not import Bootstrap |
| Authentication | Cookie session + CSRF                      | Visual login only         | Preserve real auth                                                |
| Data fetching  | Typed API client                           | Hard-coded HTML           | Preserve API truth                                                |
| RTL/LTR        | Runtime Arabic/English direction           | LTR only                  | Preserve and strengthen logical CSS                               |
| Accessibility  | Semantic React components and focus styles | Legacy template semantics | Use project components and WCAG AA tokens                         |
| Payments       | Real dormant infrastructure                | Storefront cart/checkout  | Exclude donor payment UI and hide SaaS checkout in free mode      |
| Dependencies   | 0 audited vulnerabilities                  | Legacy vendor scripts     | Add no donor runtime dependency                                   |

## Canonical build and deployment

Only `web/` is built by `scripts/vercel_build.py` and served as the SPA. The donor is not
referenced by imports, build configuration, runtime routes, or deployment rewrites. Its
source directory and archive are removed, so the repository and release scanner contain
one frontend source.
