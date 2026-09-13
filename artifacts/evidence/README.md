# Evidence Index

Last updated: 2026-08-01

This directory is reserved for concise verification evidence that is safe to keep in the
repository. Do not store secrets, raw provider tokens, private customer exports, or plaintext
operator credentials here.

Current evidence locations:

- `artifacts/baseline/`: local baseline and browser evidence from earlier acceptance work.
- `artifacts/ui-verification/`: local UI verification screenshots and route checks.
- `artifacts/production-verification/`: production browser/API/COD verification evidence.
- `artifacts/release/summary.md`: release gate summary and deployment evidence.
- `artifacts/production-readiness/final-status.md`: current launch-readiness ledger.
- `artifacts/production-readiness/owner-actions.md`: exact owner-controlled action handoff.
- `artifacts/production-readiness/environment-matrix.md`: redacted environment-variable name,
  scope, provider, rotation, and validation matrix.
- `artifacts/agent/current-state.json`: machine-readable continuation state.
- `artifacts/agent/provider-status.json`: provider activation matrix without secrets.

Latest local provider hardening evidence:

- Transactional email: `EMAIL_PROVIDER=resend` now requires `EMAIL_FROM` to be exactly one safe
  sender email address with a real domain shape and no header injection characters; focused
  validation passed via `uv run pytest tests/unit/test_config.py -q` on 2026-08-01.
- AI integration status: deterministic AI is no longer reported as configured in production,
  matching the fail-closed provider builder; focused validation passed via
  `uv run pytest tests/unit/test_integration_status.py tests/unit/test_ai_provider_runtime.py tests/unit/test_config.py -q`
  on 2026-08-01.
- Media/malware integration status: database-backed media is reported as configured, local media is
  not reported as production-configured, Cloudinary requires the full credential set, and malware
  scanner readiness is visible/fail-closed in production; focused validation passed via
  `uv run pytest -p no:cacheprovider tests/unit/test_integration_status.py tests/api/test_products_content_publishing.py::test_integrations_are_secret_safe -q`
  on 2026-08-01.
- Meta social and commerce connector provider evidence: `meta_social` and `commerce_connectors`
  are now required provider-status records, with matching redacted environment matrix and
  owner-action coverage for Facebook/Instagram publishing/inbox activation and merchant
  Shopify/WooCommerce/generic store activation; local provider, matrix, env-template, and
  owner-action verifiers passed on 2026-08-01.
- Store connection status visibility: `/api/v1/integrations` now includes current-store
  `meta_social_connections` and `commerce_connectors` aggregate statuses, reporting connected
  counts and health modes without provider tokens, ciphertext, raw account identifiers, or webhook
  secrets. The integrations page now refreshes both the connection rows and aggregate status cards
  after provider connect/check/disconnect actions; focused validation passed via
  `uv run pytest -p no:cacheprovider tests/unit/test_integration_status.py tests/api/test_provider_connections.py tests/api/test_commerce_connectors.py tests/api/test_products_content_publishing.py::test_integrations_are_secret_safe -q`
  on 2026-08-01, while frontend build could not be run because Node/npm are unavailable locally.
- Meta social connection check: `/api/v1/integrations/meta/check` now checks current-store Meta
  OAuth connections when present, returns the same secret-safe aggregate statuses, and does not
  require forbidden global merchant credentials for the OAuth path; focused validation passed via
  `uv run pytest -p no:cacheprovider tests/unit/test_integration_status.py tests/api/test_provider_connections.py tests/api/test_products_content_publishing.py::test_integrations_are_secret_safe -q`
  on 2026-08-01.
- Shopify OAuth installation: admin start/exchange endpoints now generate single-use hashed state,
  authenticated `/shopify/oauth/callback` validates signed Shopify callback HMACs before
  redirecting the browser to the integrations UI, exchange codes server-side, create encrypted
  store-scoped provider connections, use the Shopify app secret for OAuth-installed store webhook
  HMAC validation, optionally request webhook registration, and clear OAuth transaction
  credentials; the integrations UI is wired to start and exchange Shopify OAuth. Focused backend
  validation passed via
  `uv run pytest -p no:cacheprovider tests/api/test_commerce_connectors.py tests/unit/test_config.py tests/unit/test_commerce_security.py -q`
  on 2026-08-01; frontend build could not be run because Node/npm are unavailable in this runner.

Current evidence gates:

- `scripts/verify_frontend_integration_wiring.py`: validates Shopify OAuth callback/UI/API wiring
  and integration-page aggregate status refresh paths. It is wired into readiness validation and
  `scripts/verify_all.py`; focused verifier/unit/Ruff/mypy/format checks passed on 2026-08-01.
  This is a source-integrity guard, not a replacement for the Node/npm frontend build gate.
- `scripts/verify_provider_status.py`: validates the provider matrix uses only approved
  activation statuses, includes the required provider records and fields, records environment
  key names without values, and contains no secret-looking strings.
- `scripts/verify_environment_matrix.py`: validates the redacted environment matrix table,
  requires the critical runtime keys and provider-required environment key names to be present,
  and rejects secret-looking values or environment assignments.
- `scripts/verify_env_example.py`: validates the committed `.env.example` template includes
  critical runtime and provider-required key names while keeping sensitive names blank and rejecting
  secret-looking values.
- `scripts/verify_readiness_artifacts.py`: validates that required readiness artifacts exist,
  current-state evidence has the required structure, provider status, environment matrix, and
  `.env.example` evidence pass validation, the final readiness verdict does not overclaim while
  blockers remain, and top-level readiness docs start with `Not production ready` whenever
  unresolved blockers are still recorded. It also checks that `.gitignore` unignores the required
  text evidence artifacts so repository import does not accidentally drop them.
- `scripts/verify_deployment_smoke.py`: runs unauthenticated post-deploy HTTP checks against a
  Preview or Production URL for security headers, health readiness, hidden OpenAPI docs, and
  reserved API-route JSON 404 behavior.
- `scripts/verify_owner_actions.py`: validates the structured owner-action handoff includes the
  required exact fields, the current sequential blockers, later provider actions, and no
  secret-looking values. It also checks provider-required environment key names from
  `artifacts/agent/provider-status.json` are represented in the owner handoff.
- `scripts/verify_deployment_evidence.py`: validates that deployment IDs in operator and release
  evidence match `artifacts/agent/current-state.json`, preventing stale rollback/log commands.
- `scripts/verify_production_access.py`: validates `docs/PRODUCTION_ACCESS.md` against
  `artifacts/agent/current-state.json` for Vercel team/project identifiers, deployment-control key
  names, ignored local secret-file markers, safety language, and secret-looking values.
- `scripts/verify_vercel_access_evidence.py`: validates
  `artifacts/production-readiness/vercel-access.md` against current deployment identifiers and
  provider status so partial connector access cannot be overstated as production project access.
- `scripts/verify_operations_runbook.py`: validates `docs/OPERATIONS.md`,
  `docs/INCIDENT_RESPONSE.md`, and `docs/BACKUP_AND_RESTORE.md` against current deployment
  identifiers, required smoke/log/alert/worker/restore commands, restore safety language, and
  secret-looking values.
- `scripts/verify_repository_handoff_manifest.py`: validates
  `artifacts/production-readiness/repository-handoff-manifest.json`, a deterministic hash manifest
  for safe source/config/docs import into the canonical Git repository while excluding mutable
  local state, ignored secrets, build output, caches, and the manifest itself.
- `scripts/verify_release.py`: validates release source hygiene by rejecting secret-looking
  strings, local secret/state files, dependency trees, Python bytecode, `__pycache__`, and generated
  pytest/mypy/Ruff cache directories. `scripts/verify_all.py` runs pytest/Ruff/mypy in cache-safe
  mode before invoking this final scan.
