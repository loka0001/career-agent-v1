# Production Release Evidence

Date: 2026-07-31

## Deployment

- Canonical URL: `https://commerce-revenue-autopilot.vercel.app`
- Vercel deployment: `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx`
- Immutable URL:
  `https://commerce-revenue-autopilot-esujrvt5r-malek-virtz.vercel.app`
- Status: Ready
- Entry bundle: `assets/index-S7SWn1Lj.js`
- Migration head: `20260729_0028`
- Liveness/readiness: HTTP 200; database, search, and job queue true

## Source and Database Gates

- Ruff check: passed.
- Ruff format check: passed for 115 Python files.
- Strict mypy: passed for 120 application and script source files.
- Pytest: 150 tests passed.
- Managed PostgreSQL migration: before/after `20260729_0028`.
- Clean and prior-schema upgrade paths: reached head.
- Post-verifier readiness: remained HTTP 200 across repeated runs.
- Fresh `npm ci`: 194 packages installed, 0 known vulnerabilities.
- ESLint: passed.
- Vitest: 8 tests in 4 files passed.
- TypeScript/Vite: passed; 519 modules transformed.
- Release credential/local-state/binary/dependency scan: passed.
- Release hygiene gate tightened: `scripts/verify_release.py` now fails on
  `__pycache__`, `.pyc`, `.pyo`, `.pytest_cache`, `.mypy_cache`, and `.ruff_cache`
  artifacts; generated caches were removed before the final release scan, and
  `scripts/verify_all.py` runs pytest/Ruff/mypy in cache-safe mode before invoking
  the scan. Text files under `artifacts/` are now included in the secret/local-state
  scan while binary screenshots remain skipped by suffix.
- Python dependency audit: `pip-audit -r requirements.txt` initially found five
  advisories in `cryptography 46.0.5`; the project now pins `cryptography 48.0.1`
  and the follow-up audit reported no known vulnerabilities.
- Rate-limit hardening/evidence: removed the stale unused in-process limiter,
  documented database-backed `rate_limit_buckets`, and added public endpoint HTTP
  429 regression coverage.
- Backup/restore drill hardening: `scripts/verify_backup_restore.py` now restores
  representative commerce tables, validates the migration marker, row counts, COD
  order totals, background jobs, and tenant-boundary joins. Production backup safety
  still requires an owner-authorized provider backup restored into a separate
  non-production destination.
- Operations readiness warnings: production configuration now reports missing
  `OPERATOR_EMAILS`, `SENTRY_DSN`, and `RELEASE_SHA` as redacted readiness issues.
- Operator alert coverage: `/api/v1/operator/alerts` now reports production readiness gaps as
  stable redacted issue codes, alongside queue and provider connection alerts.
- Standalone worker health: `JobWorker.health()` now tracks fresh successful polls and
  `scripts.worker` returns HTTP 503 from `/health/ready` when the worker is stale or degraded,
  with redacted error codes only.
- Production worker runtime preflight: `scripts.worker` now fails closed in production unless
  the persistent worker is explicitly enabled with `ENABLE_BACKGROUND_WORKER=true`, is not running
  as serverless, and uses PostgreSQL. The in-app operator alert matrix maps this gap to
  `worker_runtime_missing`.
- Git release integrity: `scripts/verify_git_integrity.py --require-release-sha` now checks
  clean Git state, remote presence, a full release SHA, and release SHA matching `HEAD`. It is
  wired into CI and `scripts/verify_all.py`; this local snapshot still fails because `.git`
  metadata is absent.
- Provider activation evidence: `scripts/verify_provider_status.py` now validates
  `artifacts/agent/provider-status.json` for the approved status vocabulary, required provider
  records and fields, timestamp syntax, environment-key names without values, and secret-looking
  strings. It is wired into GitHub Actions and `scripts/verify_all.py`.
- Meta social and commerce connector evidence: `meta_social` and `commerce_connectors` are now
  required provider-status records, with matching environment-matrix and owner-action handoff
  coverage for Facebook/Instagram publishing/inbox activation and merchant store connector
  activation.
- Meta social connection check hardening: `/api/v1/integrations/meta/check` now checks
  current-store Meta OAuth connections when present and reports secret-safe aggregate connection
  status without requiring forbidden global merchant credentials in the OAuth path.
- Integration status refresh hardening: the integrations page now refreshes both connection rows
  and `/api/v1/integrations` aggregate status cards after provider connect/check/disconnect
  actions, reducing stale operator-facing provider state.
- Frontend integration wiring guard: `scripts/verify_frontend_integration_wiring.py` now checks
  Shopify OAuth callback/UI/API wiring plus integration-page aggregate status refresh paths, and is
  wired into readiness and release verification. This guards source drift while Node/npm remain
  unavailable locally, but it does not replace the frontend lint/test/build gate.
- Shopify OAuth installation hardening: admin start/exchange endpoints now use single-use hashed
  OAuth state, authenticated `/shopify/oauth/callback` validates Shopify callback HMACs before
  redirecting the browser to the integrations UI, exchange codes server-side, create encrypted
  store-scoped provider connections, use the Shopify app secret for OAuth-installed store webhook
  HMAC validation, optionally request webhook registration, and clear OAuth transaction
  credentials after completion. The integrations UI is wired to launch and complete Shopify OAuth;
  live merchant-store acceptance remains external, and frontend build remains blocked locally by
  missing Node/npm.
- Environment matrix integrity: `scripts/verify_environment_matrix.py` now validates the redacted
  `artifacts/production-readiness/environment-matrix.md` table, requires critical runtime keys and
  provider-required environment key names from `artifacts/agent/provider-status.json`, and rejects
  secret-looking values or accidental `KEY=value` entries. It is wired into GitHub Actions,
  `scripts/verify_all.py`, and readiness-artifact validation.
- Environment template integrity: `.env.example` now lists the operator/CI-only Vercel and
  backup-restore key names without values, and `scripts/verify_env_example.py` validates critical
  runtime and provider-required key coverage while rejecting committed sensitive placeholders. It
  is wired into GitHub Actions, `scripts/verify_all.py`, and readiness-artifact validation.
- Readiness artifact integrity: `scripts/verify_readiness_artifacts.py` now validates the required
  readiness artifacts, current-state schema, provider-status evidence, and the honest final
  verdict. It is wired into GitHub Actions and `scripts/verify_all.py`.
- Top-level readiness verdict honesty: `PRODUCTION_READINESS.md` now starts with
  `Not production ready` while unresolved blockers remain. `scripts/verify_readiness_artifacts.py`
  rejects a top-level ready claim whenever `current-state.json` still records blockers.
- Git handoff artifact preservation: `.gitignore` now unignores required text evidence artifacts
  under `artifacts/agent/`, `artifacts/evidence/`, `artifacts/production-readiness/`, and
  `artifacts/release/`, while keeping bulky evidence directories ignored. The readiness verifier
  rejects ignore rules that would hide required evidence during canonical repository import.
- Owner-action handoff integrity: `artifacts/production-readiness/owner-actions.md` now records
  the exact sequential owner-controlled actions, fields, value sources, reasons, expected results,
  and verification steps. `scripts/verify_owner_actions.py` validates it without exposing secrets
  and cross-checks provider-required environment key names from
  `artifacts/agent/provider-status.json`.
- Production access evidence integrity: `docs/PRODUCTION_ACCESS.md` now records Vercel
  deployment-control key names only, while `scripts/verify_production_access.py` validates Vercel
  team/project identifiers against `artifacts/agent/current-state.json`, required local
  secret-file markers, access safety language, and secret-looking values.
- Deployment evidence integrity: `scripts/verify_deployment_evidence.py` now rejects stale
  deployment IDs in operator and release evidence. It caught the old incident-response deployment
  command, which now points at `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx`. GitHub Actions runs the
  verifier directly as well as through readiness-artifact validation.
- Formal release type gate: `scripts/verify_all.py` now runs
  `python -m mypy --strict app scripts`, matching the documented local and CI command and covering
  release/operation scripts.
- Deployment smoke gate: `scripts/verify_deployment_smoke.py` now provides a repeatable
  unauthenticated Preview/Production HTTP gate for security headers, liveness, readiness,
  production-hidden OpenAPI, and reserved API-route JSON 404 behavior.
- Formal release wiring: `scripts/verify_all.py` now accepts `--deployment-url` and runs the
  deployment smoke gate as part of the release command when a Preview or Production URL is
  supplied.
- Current production deployment smoke: the new gate was run against
  `https://commerce-revenue-autopilot.vercel.app` on 2026-08-01 and failed because production
  still serves the old behavior: `/openapi.json` returned HTTP 200 HTML instead of JSON 404, and
  `/api/v1/conversations` returned HTTP 503 HTML instead of JSON 404. This confirms a new Vercel
  deployment is required before the local route-hardening fix can be production-verified.

## Production API and Commerce Acceptance

- Authenticated core API reads: 21 passed, 0 failed.
- Production mode: `demo_mode=false`.
- Access policy: internal free access, no checkout or portal.
- Dashboard: HTTP 200.
- Unknown reserved route fallback hardened locally: `/api/v1/conversations`,
  `/openapi.json`, `/health/*`, webhooks, checkout, and media paths now return JSON
  404 with no-store caching. Production verification is pending Vercel reauthentication.
- Production smoke after the local change: `/health/live` and `/health/ready` returned
  HTTP 200 on 2026-07-31, while `/api/v1/conversations` still returned the old HTTP
  503 HTML fallback. A new deployment is required before this fix can be production-verified.
- Operator alert visibility hardened locally: `/api/v1/operator/alerts` reports
  dead-lettered jobs, queue backlog age, stale leases, and provider attention states
  without exposing job payloads, raw errors, or secrets.
- Order lifecycle:
  - created as `draft`;
  - COD checkout confirmed as `confirmed` and `awaiting_cash`;
  - cancellation completed;
  - stock changed 40 → 39 → 40.
- Known local-Demo seed password: rotated in production; old rejected, replacement
  accepted, plaintext not stored in the repository.

## Production Browser Acceptance

- 20 authenticated routes.
- Arabic RTL and English LTR.
- Desktop 1440 and mobile 390 layouts.
- Mobile navigation visible and no horizontal overflow.
- No Demo inbound simulation control.
- No plan grid or card input.
- No console errors, page errors, failed requests, or HTTP error responses.
- Screenshots: `artifacts/production-verification/`.

## Security Headers

- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
- Cross-Origin-Opener-Policy

## External Boundary

Stripe, Meta social, WhatsApp, commerce connectors, OpenAI, transactional email, and external
object-media providers remain unverified until merchant credentials and provider acceptance are
supplied. Shopify OAuth is implemented locally but still awaits credentialed merchant-store
acceptance. Timely scheduled work requires a Pro-or-higher Vercel cron or an independent worker;
Docker/Trivy remains a Docker-capable runner gate.
