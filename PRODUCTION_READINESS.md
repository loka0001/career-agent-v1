# Production Readiness

Last reconciled: 2026-09-05. Deployment identifiers and results below are a historical
2026-08-01 evidence checkpoint; the current hardening candidate has not been deployed or
independently live-verified.

## Current Verdict

`Not production ready - core deployment verified; ownership, provider activation, backup restore,
launch-grade worker scheduling, and deployment of local hardening remain incomplete`

Historical checkpoint label, superseded by the current verdict above:

`DEPLOYED — CORE RELEASE VERIFIED; EXTERNAL PROVIDER ACTIVATION PENDING`

The 2026-08-01 evidence ledger recorded production checks for the then-deployed release. It is not
proof for the current working tree. The candidate adds migration `20260902_0030`; clean/upgrade
migrations and a representative logical restore now pass on disposable local PostgreSQL 17.10,
while managed PostgreSQL, deployment, worker and provider acceptance remain outstanding.
Merchant-owned provider accounts, legal approvals, and a launch-grade scheduler/worker remain
activation work and are not represented as live.

## Production Deployment

| Item | Value |
| --- | --- |
| Canonical URL | `https://commerce-revenue-autopilot.vercel.app` |
| Vercel deployment | `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx` |
| Immutable URL | `https://commerce-revenue-autopilot-esujrvt5r-malek-virtz.vercel.app` |
| Historical status | Ready at the recorded checkpoint; current access is blocked |
| Entry asset | `assets/index-S7SWn1Lj.js` |
| Database | Managed PostgreSQL with TLS |
| Historical deployed migration head | `20260729_0028` |
| Current candidate migration head | `20260902_0030` (clean/upgrade and logical restore verified locally; not deployed or managed-provider verified) |
| Function bundle | 56.8 MB |
| Merchant collection | Cash on delivery |
| SaaS access | Free active Growth access; no card and no trial expiry |

Production does not fall back to SQLite, deterministic AI, fake publishing, Demo
checkout, or inbound simulation. Builds do not run migrations or seed data.

## Code and Release Gates

| Area | State |
| --- | --- |
| Production/Demo separation | Historical production evidence plus current local tests; candidate deployment unverified |
| Tenant isolation and encrypted credentials | Complete; automated coverage |
| Auth, MFA, invitations, onboarding, RBAC, CSRF | Complete |
| Database-backed rate limiting | Complete locally; service and public HTTP 429 coverage passed |
| Free access and entitlements | Complete; Growth active, no trial/card/provider IDs, quotas retained |
| Billing safety | Complete; checkout/portal disabled, no production plan/card UI |
| Catalog, inventory, orders, COD | Historical production lifecycle evidence; current candidate requires acceptance rerun |
| Worker, retries, leases, replay, cron | Complete contract; standalone worker readiness health and production runtime preflight hardened locally; independent runtime activation pending |
| Unknown API route handling | Completed locally; deployment pending Vercel reauthentication |
| AI measurement and controls | Complete contract; provider key pending; operator-facing integration status now matches production fail-closed behavior and does not report deterministic AI as configured in production |
| Transactional email sender guard | Hardened locally; `EMAIL_PROVIDER=resend` now requires `EMAIL_FROM` to be exactly one safe sender email address with a real domain shape and no header injection characters; focused config tests passed |
| WhatsApp webhook phone scoping | Hardened locally; signed webhook processing now ignores message/status events whose `metadata.phone_number_id` does not match the configured channel phone-number ID, with API coverage |
| Media and malware status | Hardened locally; operator-facing integration status now reports database-backed media as configured, local media as not production-configured, Cloudinary as configured only with the full credential set, and malware scanning as visible/fail-closed in production |
| Meta social provider evidence | Hardened locally; `meta_social` is now a required provider-evidence row for Facebook/Instagram publishing, DM/comment webhooks, OAuth/account review, and credentialed smoke tests instead of being implied by WhatsApp evidence |
| Meta social connection check | Hardened locally; `/api/v1/integrations/meta/check` now checks current-store Meta OAuth connections when present, returns secret-safe aggregate status, and avoids forbidden global publisher credentials in the per-store OAuth path |
| Commerce connector provider evidence | Hardened locally; `commerce_connectors` is now a required provider-evidence row for Shopify/WooCommerce/generic store activation, per-store encrypted credentials, Shopify OAuth install/exchange, sync/webhook verification, and live merchant-store acceptance |
| Shopify OAuth installation | Hardened locally; start/exchange endpoints and authenticated `/shopify/oauth/callback` now support the browser install round trip, using hashed single-use state, signed HMAC callback validation, invalid-signature rejection before state consumption, server-side token exchange, encrypted provider-connection creation, Shopify app-secret webhook verification for OAuth installs, optional webhook registration, and transaction cleanup; integrations UI is wired to start/exchange OAuth, and frontend lint/tests/coverage/build pass |
| Store connection status visibility | Hardened locally; `/api/v1/integrations` now includes secret-safe aggregate statuses for per-store Meta social connections and commerce connectors, using counts and health modes instead of provider tokens or account identifiers; integration-page connect/check/disconnect flows now refresh both connection rows and aggregate status cards from the API |
| Privacy, retention, deletion, private media | Complete contract; legal/provider activation pending |
| Canonical responsive frontend | Complete; one React SPA, Arabic RTL / English LTR |
| Source/dependency/artifact scanning | Complete; release gate scans source and text evidence artifacts |
| Frontend integration wiring guard | Hardened locally; `scripts/verify_frontend_integration_wiring.py` now checks that Shopify OAuth callback/UI/API wiring and integration-page aggregate status refresh paths stay present, and is wired into readiness/release verification; this does not replace the Node/npm frontend build gate |
| Python dependency audit | Complete locally; `pip-audit -r requirements.txt` clean after `cryptography` upgrade |
| Release bytecode/cache hygiene | Complete locally; verifier rejects Python bytecode, `__pycache__`, `.pytest_cache`, `.mypy_cache`, and `.ruff_cache`; `scripts/verify_all.py` now disables or redirects those tool caches before running the release scan |
| Backup/restore drill | Passed on disposable PostgreSQL 17.10 with matching `pg_dump`/`pg_restore`; restores representative commerce tables and validates migration marker, row counts, COD totals, background jobs, and tenant joins; provider backup restore remains pending |
| Operations readiness warnings | Hardened locally; production startup and operator alerts now report missing operator allowlist, external monitoring, release SHA, and other readiness gaps as redacted issue codes |
| Git release integrity | Hardened locally; CI and `verify_all.py` now run `scripts/verify_git_integrity.py --require-release-sha` to require clean Git checkout, remote, and release SHA matching `HEAD` |
| Provider evidence integrity | Hardened locally; GitHub Actions and `scripts/verify_all.py` run `scripts/verify_provider_status.py` to validate the provider matrix status vocabulary, required fields, timestamp syntax, required provider coverage, environment key names without values, and secret-looking string patterns |
| Environment matrix integrity | Hardened locally; GitHub Actions, `scripts/verify_all.py`, and readiness-artifact validation now run `scripts/verify_environment_matrix.py` to require critical runtime keys and provider-required environment key names in the redacted matrix without values |
| Environment template integrity | Hardened locally; `.env.example` now includes operator/CI-only Vercel and backup-restore variable names without values, and `scripts/verify_env_example.py` validates required key coverage plus blank sensitive template values in CI/release gates |
| Owner-action handoff integrity | Hardened locally; `artifacts/production-readiness/owner-actions.md` records exact owner-controlled actions, pages, fields, value sources, expected results, and verification steps; `scripts/verify_owner_actions.py` validates it without secret values and cross-checks provider-required key names |
| Production access evidence integrity | Hardened locally; `docs/PRODUCTION_ACCESS.md` now records Vercel deployment-control key names only, and `scripts/verify_production_access.py` validates Vercel team/project identifiers, local secret-file markers, safety language, and secret-looking values |
| Vercel access evidence integrity | Hardened locally; `artifacts/production-readiness/vercel-access.md` records the connector result that `malek-virtz` is visible but `commerce-revenue-autopilot` is not listed/resolvable, and `scripts/verify_vercel_access_evidence.py` keeps the deployment-control status at `blocked_missing_access` until the production project is accessible |
| Operations runbook integrity | Hardened locally; GitHub Actions, `scripts/verify_all.py`, and readiness-artifact validation now run `scripts/verify_operations_runbook.py` to require current deployment identifiers, smoke/log/alert/worker commands, restore drill commands, restore safety language, and no secret-looking values across operations, incident response, and backup/restore docs |
| Repository handoff integrity | Hardened locally; `artifacts/production-readiness/repository-handoff-manifest.json` records deterministic SHA-256 hashes for source, tests, configs, docs, workflows, and stable evidence artifacts so canonical Git import can verify the local tree without including secrets, caches, build output, mutable agent state, or the manifest itself |
| Deployment evidence integrity | Hardened locally; GitHub Actions and `scripts/verify_all.py` run `scripts/verify_deployment_evidence.py` to reject stale deployment IDs in release and operations evidence, and the incident-response commands now point at `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx` |
| Readiness artifact integrity | Hardened locally; GitHub Actions and `scripts/verify_all.py` run `scripts/verify_readiness_artifacts.py` to require the mandated readiness artifacts, current-state structure, valid provider evidence, valid owner-action handoff, and a non-overclaiming final verdict while blockers remain |
| Git handoff artifact preservation | Hardened locally; `.gitignore` now keeps required text evidence artifacts addable while ignoring bulky evidence directories, and `scripts/verify_readiness_artifacts.py` rejects ignore rules that hide required readiness artifacts |
| Readiness verdict honesty | Hardened locally; `PRODUCTION_READINESS.md` now starts with `Not production ready` while unresolved blockers remain, and `scripts/verify_readiness_artifacts.py` enforces that top-level verdict |
| Formal release type gate | Hardened locally; `scripts/verify_all.py` now matches the documented CI command by running `python -m mypy --strict app scripts` instead of non-strict `mypy app` |
| Deployment smoke gate | Hardened locally; `scripts/verify_deployment_smoke.py` checks public security headers, `/health/live`, `/health/ready`, hidden `/openapi.json`, and reserved API JSON 404 behavior against Preview or Production URLs; `scripts/verify_all.py --deployment-url ...` runs it during formal release verification |
| Container scanning | Configured; Docker-capable runner required |

## Historical Production Acceptance (2026-08-01)

The results in this section belong to the recorded deployment above. They must not be reused as
acceptance evidence for the current candidate.

- Liveness: HTTP 200.
- Readiness: HTTP 200 with database, search, and job queue all true.
- Migration: before and after historical head `20260729_0028`; current head `20260902_0030` is pending.
- Clean/prior-schema verification: both upgrade paths reached head.
- Post-verifier readiness: HTTP 200 across repeated runs.
- Authenticated API: 21 of 21 core reads passed.
- Dashboard: HTTP 200 after the PostgreSQL JSON portability correction.
- COD journey: draft → confirmed/`awaiting_cash` → cancelled; stock 40 → 39 → 40.
- Browser: 20 authenticated routes, Arabic RTL, English LTR, desktop and mobile.
- Browser runtime: no console/page/request/HTTP errors and no horizontal overflow.
- Production-only UX: no inbound simulator, plan cards, card input, or checkout.
- Security headers: CSP, HSTS, nosniff, DENY framing, strict referrer policy,
  permissions policy, and COOP.
- Credential hygiene: the known seed password was rotated; old login rejected and
  new login accepted.
- Fallback hardening: unknown reserved routes such as `/api/v1/conversations`,
  `/openapi.json`, `/health/*`, webhooks, checkout, and media paths now fail closed
  with JSON 404 locally instead of falling through to the frontend fallback. Production
  deployment and live verification require Vercel reauthentication.
- Deployment smoke gate: `scripts/verify_deployment_smoke.py` now checks security headers,
  health readiness, production-hidden `/openapi.json`, and reserved API JSON 404 behavior against
  Preview or Production URLs. Running it against the current production URL on 2026-08-01 failed
  because the local route-hardening change is still not deployed.
- Backup/restore drill: `scripts/verify_backup_restore.py` now exercises a restored
  commerce fixture across core tables and tenant-boundary joins. Production database
  safety still requires a real provider backup restored into a separate non-production
  destination.
- Operations readiness warnings: production settings now report missing `OPERATOR_EMAILS`,
  `SENTRY_DSN`, and `RELEASE_SHA` alongside the existing provider/security warnings, without
  exposing secret values. `/api/v1/operator/alerts` now includes the same configuration state
  as stable redacted issue codes.
- Standalone worker health: `scripts.worker` now returns readiness based on fresh successful
  queue polls, exposes redacted health fields, and returns HTTP 503 from `/health/ready` when
  the worker is stale or degraded. A production always-on worker runtime is still not activated.
- Worker runtime preflight: `scripts.worker` now refuses production startup unless the persistent
  worker is explicitly enabled, non-serverless, and PostgreSQL-backed. `/api/v1/operator/alerts`
  maps the missing activation flag to `worker_runtime_missing`.
- Git release integrity: `scripts/verify_git_integrity.py` now enforces clean Git checkout,
  remote presence, and `RELEASE_SHA`/`GITHUB_SHA` matching `HEAD` in CI and formal release gates.
  This local workspace still fails the release gate because it has no configured remote or
  immutable release SHA and the verified candidate is not yet committed.
- Environment matrix integrity: `scripts/verify_environment_matrix.py` now validates
  `artifacts/production-readiness/environment-matrix.md`, checks provider-required environment
  key names against `artifacts/agent/provider-status.json`, and rejects secret-looking values or
  accidental assignments.
- Environment template integrity: `scripts/verify_env_example.py` now validates `.env.example`
  against critical runtime and provider-required names, while rejecting secret-looking values and
  committed sensitive placeholders.
- WhatsApp webhook phone scoping: signed WhatsApp webhooks now validate the configured
  phone-number ID before processing inbound messages or status updates. The API regression test
  confirms a signed event for another `phone_number_id` returns `processed=0` and creates no
  message.

## Historical Live Verification Classification

“Live verified” in this table means the 2026-08-01 evidence ledger reported the result for the
historical deployment. Current candidate status is **unverified** until all acceptance gates are
repeated for one immutable release SHA.

| Integration | Classification |
| --- | --- |
| Managed PostgreSQL | Historical live evidence at `0028`; current `0029` candidate unverified |
| Vercel web/API | Historical Ready/API/browser evidence; current candidate unverified and project access blocked |
| Internal free access | Historical live evidence; current candidate locally verified only |
| COD order collection | Historical live evidence; current candidate acceptance pending |
| Durable queue readiness/recovery | Historical serverless diagnostic evidence; persistent production worker still blocked |
| Stripe | Code complete, intentionally dormant |
| Meta/Instagram/Facebook | Code complete, external activation required |
| WhatsApp Business | Code complete, external activation required |
| OpenAI | Code complete, external activation required |
| Facebook/Instagram social publishing and inbox | Code complete, external activation required |
| Transactional email | Code complete, external activation required |
| Commerce connectors | Local connector contract and Shopify OAuth installation verified; external merchant store activation required |
| External object media/ClamAV | Hook complete, external activation required |
| Operator alert rules | Completed locally; production deployment pending Vercel reauthentication |

Never mark an external integration “live verified” without recording the account,
environment, date, test cases, and redacted provider references.
