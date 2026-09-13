# Implementation Status

Last reconciled: 2026-09-13

This document reports the current working tree. Historical deployment evidence is explicitly
separate from current-candidate verification.

## Current phase

The local product and its two primary demo journeys are operational. P0 hardening, repository truth
mapping, threat modeling, security-diff review, documentation reconciliation, clean bootstrap, and
broad UI verification are complete. Current-market UI research selected Gorgias as the primary
product-grammar reference, with Shopify Admin and Sprout Social as narrowly scoped secondary
references. The preferred website sequence through Inbox, Products, Content/Calendar, Integrations,
and Settings is browser-verified. Local PostgreSQL
clean/upgrade migrations and representative logical restore are also verified. Managed production
migration/restore, deployment, live-provider and merchant acceptance remain external gates.

- Canonical frontend: React/Vite SPA in `web/`.
- Backend: FastAPI, SQLAlchemy/Alembic, first-party sessions and store-scoped repositories.
- Current migration head: `20260902_0030`.
- Baseline Git commit: `f6f918a79ca4dd1aebe09df129b5755945955e89`.
- Historical deployment reference: `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx` at
  `https://commerce-revenue-autopilot.vercel.app`; current candidate unverified there.

## Capability classification

| Vertical slice                                              | Implementation and test truth                                                                                                                                                                        | Runtime truth                                                                                                                             |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Auth, MFA, recovery, sessions, CSRF, RBAC, tenant isolation | Implemented and automated, including global expired-session handling and useful feature/operator denial states                                                                                       | Clean local login, expired-session redirect/notice, and permission-denied UI verified; deployed candidate unverified                      |
| Catalog, inventory, orders, COD                             | Implemented and automated                                                                                                                                                                            | Local demo and historical evidence; current deployed acceptance pending                                                                   |
| Unified inbox and grounded sales                            | Implemented, citations validated/rendered, reply idempotency/audit tested, eight adversarial vectors verified, and a real customer/order context rail added from existing APIs                    | Clean local browser and worker verified in Arabic/English and desktop/mobile; credentialed live-AI/channels unverified                     |
| Opportunities and automations                               | Implemented with persisted approvals/jobs                                                                                                                                                            | Automated/local capability; production scheduler/worker unverified                                                                        |
| Content Studio and publishing                               | Versioned approval hash, worker revalidation, and localized actionable failed/retrying/unknown publication states implemented/tested                                                                | Clean local browser demo publication plus intercepted publish-failure UI verified; live Meta unverified                                    |
| Meta/WhatsApp webhooks and adapters                         | Signed, deduplicated, store-scoped implementation/test coverage                                                                                                                                      | No current credentialed acceptance                                                                                                        |
| Commerce connectors                                         | OAuth/direct-token and SSRF-safe connector contracts implemented/tested                                                                                                                              | No merchant-store acceptance                                                                                                              |
| Privacy and private media                                   | Export/retention/deletion and signed media implemented/tested                                                                                                                                        | Local verified; production storage/operations unverified                                                                                  |
| Durable runtime                                             | Database job queue, explicit complete handler registry, lease/retry/dead-letter, worker preflight, and a pre-call external-operation ledger prevent blind resend after an ambiguous provider outcome | Local independent worker verified on outbound and publication jobs; production process and live-provider reconciliation remain unverified |
| Observability and operations                                | Health, structured logging, operator alerts and runbooks implemented/tested                                                                                                                          | Alert destination and deployed telemetry unverified                                                                                       |

The detailed independent columns for code, tests, demo and live status are maintained in
`docs/REPOSITORY_TRUTH_AUDIT.md`.

## Current verification state

- 2026-09-12 website completion checkpoint: the ThemeForest Furns customization is applied across the public and authenticated website without replacing real API behavior. Team, Security, and API Keys received bilingual operational states and desktop workspace layouts. The full browser gate passes 20 authenticated routes, Arabic/English, 1440/768/390 widths, COD, provider/AI/network/permission/session states, and reports no unexpected console, page, request, response, accessibility-label, or overflow failures.

- Python lint, formatting and strict typing: pass.
- Frontend lint, 96 tests across 22 files, a full coverage run (66.99% statements, 60.53%
  branches, 64.36% functions, and 68.35% lines), and production build: pass. The current coverage
  denominator includes the newly imported Integrations implementation.
- Vitest and its V8 coverage package are pinned to 4.1.11; the transitive mocker now enforces the
  Vite file-serving allowlist for GHSA-82fw-gwwq-j7x9. A fresh install and npm audit report zero
  vulnerabilities. This is development-tool remediation, not an application production-security claim.
- Complete backend functional suite: 312 collected, 307 passed and 5 intentionally skipped.
- Final local release gate on 2026-09-13: Ruff check/format, strict mypy over 169 source
  files, readiness/handoff verification, frontend Prettier/ESLint/logical CSS, all 96 Vitest
  tests, and the production Vite build pass. Login abuse protection now uses a rolling
  per-second bucket window, and handoff verification excludes named local virtualenvs.
- Catalog list/detail supports query-preserving links, review/activation, provider/role boundaries, retry and discard. On 2026-09-08 all 306 backend tests passed. The extended `verify:catalog` gate proves bilingual 1440/768/390 layouts, variant opening-stock ledger and signed adjustments, and product onboarding through edited, explicitly approved demo publication. The creation wizard is bilingual; ambiguous inventory retries retain their request key across remounts. Multiple-variant aggregate stock is read-only; manual provider-owned mutations and conflicting request-key reuse are rejected. Live publication remains unverified.
- Inbox async results are bound to the selected conversation; delayed sends cannot reopen a previous customer. The context rail distinguishes unavailable orders from an empty recent list, links to the correct customer, and uses each order's currency. Unqualified mixed-currency lifetime spend is omitted.
- Focused AI grounding audit: pass for all required adversarial customer vectors and hostile
  structured model replies; deterministic evidence only, not credentialed OpenAI acceptance.
- Clean lockfile bootstrap from a relocated candidate checkout: pass.
- Dedicated `verify:journeys` browser sales and content journeys with a persistent worker: pass on
  the current isolated candidate; the bilingual store and brand profiles saved, survived reload,
  and restored their original values before three grounding citations, exactly one added sent
  reply, one generated draft, merchant edit, recorded approval, and final published status were
  observed with zero browser errors.
- Content review now opens as a compact queue; the full draft creator is explicitly disclosed and
  URL-backed, while focused review and multi-editor views retain filters and unsaved-caption locks.
  Fresh Arabic/English 1440/768/390 screenshots and real-worker interaction checks pass.
- Integrations now defaults to a compact status overview with URL-backed Store, Meta and WhatsApp
  workspaces. OAuth callbacks select the correct completion workspace, and desktop browser evidence
  covers disconnected, Store setup and WhatsApp setup states.
- Store Settings now groups profile, brand identity and authoritative policies, exposes saved/dirty
  state, disables Save until needed, and restores the server snapshot through Discard. The desktop
  browser verifier proves edit/discard without a backend mutation.
- Broad UI verifier: pass across 20 routes, Arabic/English, three public breakpoints, theme/device
  states, the COD order lifecycle, loading, empty, network-unavailable, provider-disconnected,
  AI-unavailable, publish-failed, Home partial-source failure, permission-denied, and
  expired-session states, with zero
  unexpected console/page/request/response errors. The disconnected-provider run also verifies the
  focused website workspaces and desktop setup hierarchy. Dedicated Inbox captures also verify the real customer/commerce context rail in English
  desktop, Arabic desktop, and Arabic mobile layouts without horizontal overflow.
- The required research decision, functional mapping, and durable execution checkpoint now live in
  `docs/UI_REFERENCE_RESEARCH.md`, `docs/UI_CLONE_MAPPING.md`, and
  `docs/AGENT_EXECUTION_STATE.md`.
- Home now derives actionable reply, content-review, publishing, channel-health, order, and
  response-time summaries from the typed store APIs with per-source failure isolation. The shell's
  unbacked sample notifications were removed rather than presented as real merchant events.
- Primary navigation is limited to the six P0 merchant jobs. Existing non-P0 modules remain
  available through an accessible secondary disclosure, mobile drawer, direct routes, and command
  palette; dormant Billing is not advertised during free access.
- Portable handoff manifest and source-only release scan: pass in a clean candidate checkout; the
  manifest now retains committed seed inputs and legitimate security-named source such as
  `credential_vault.py` while still excluding runtime data and credential exports.
- Disposable PostgreSQL 17.10 clean and `0024 → head` migrations plus representative
  `pg_dump`/`pg_restore`: pass locally; the run exposed and fixed release-environment, Alembic schema,
  percent-encoded URL, and restore-query defects.
- Eight repository-local skills now validate, including dedicated proven workflows for core sales,
  content publication, frontend QA, handoff synchronization, grounding, bootstrap, orientation, and
  release gating. Real Meta/WhatsApp acceptance skills remain deferred until credentialed runs exist.
- Managed PostgreSQL/provider-backup repetition, deployment, production worker and provider
  acceptance: blocked by missing external access/credentials.

## Non-negotiable invariants

- Database facts remain authoritative for price, stock, order and policy decisions.
- Every external content action uses explicit approval evidence or an intentionally approved
  automation contract.
- Tenant/store scope is server-derived; browser identifiers never grant access by themselves.
- Demo adapters and deterministic AI are labelled as demo and never promoted to live proof.
- Secrets, reusable passwords and customer message bodies do not belong in source or evidence.
- Provider acceptance is recorded separately per provider, environment, date and release SHA.

## Next executable work

1. Preserve the completed local website candidate and repeat the browser/release gates against the
   immutable deployed SHA; Team, Security, API Keys, and Agent Settings are already locally
   complete and bilingual.
2. Configure an approved Git remote/release branch and run CI for an immutable SHA.
3. Repeat PostgreSQL migration/restore against the immutable candidate on the approved managed
   service, deploy web and persistent worker, and execute each
   credentialed provider plus merchant acceptance track.
