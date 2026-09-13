# Release Process

Last reviewed: 2026-09-01

## Source Integrity

The canonical local Git worktree exists at baseline
`f6f918a79ca4dd1aebe09df129b5755945955e89`, but no remote or immutable release SHA is configured
and the candidate is dirty during verification. Configure the approved canonical remote and create
a protected release branch only after the candidate gates pass.

## Local Gates

```powershell
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run mypy --strict app scripts
uv run pytest -q
npm --prefix web ci
npm --prefix web run lint
npm --prefix web run format:check
npm --prefix web run test
npm --prefix web run test:coverage
npm --prefix web run build
uv run python scripts/verify_git_integrity.py --require-release-sha
uv run python scripts/verify_provider_status.py
uv run python scripts/verify_environment_matrix.py
uv run python scripts/verify_env_example.py
uv run python scripts/verify_owner_actions.py
uv run python scripts/verify_production_access.py
uv run python scripts/verify_deployment_evidence.py
uv run python scripts/verify_readiness_artifacts.py
uv run python scripts/verify_release.py
```

`scripts/verify_git_integrity.py` requires a real Git worktree, a full 40-character release SHA
from `RELEASE_SHA` or `GITHUB_SHA`, a clean working tree, and a configured remote. This workspace
currently fails the release form of that gate because the verified candidate is not yet committed
and no remote/release SHA is configured.

`scripts/verify_all.py` intentionally uses the same strict Python type gate as CI:
`python -m mypy --strict app scripts`.

The repository intentionally keeps bulky generated evidence ignored while allowing the required
text evidence artifacts to be added normally. Do not replace the scoped `artifacts/*` ignore rules
with a broad `artifacts/` ignore unless the required `!artifacts/...` exceptions are preserved.

`scripts/verify_provider_status.py` checks the redacted provider activation matrix.
`scripts/verify_environment_matrix.py` checks the redacted environment-variable matrix and ensures
provider-required key names are represented without values.
`scripts/verify_env_example.py` checks the committed `.env.example` template includes required
runtime/provider key names without committed sensitive values.
`scripts/verify_owner_actions.py` checks the structured owner-action handoff for exact fields,
provider-required key-name coverage, and secret-looking values.
`scripts/verify_production_access.py` checks Vercel team/project identifiers, deployment-control
key names, local secret-file markers, and production access safety language.
`scripts/verify_deployment_evidence.py` checks that deployment IDs in
operator and release evidence match the latest known deployment ID in
`artifacts/agent/current-state.json`. `scripts/verify_readiness_artifacts.py` checks that required
readiness artifacts exist, current state has the required structure, provider status, environment
matrix, `.env.example`, owner-action, production-access, and deployment evidence validation pass,
and the final readiness verdict remains `Not production ready` while unresolved blockers are
present.

Run migration and backup gates against disposable PostgreSQL:

```powershell
$env:VERIFY_POSTGRES_URL = '<disposable-postgres-url>'
uv run python scripts/verify_backup_restore.py
uv run python scripts/verify_all.py --postgres-url $env:VERIFY_POSTGRES_URL
```

The backup/restore drill uses a temporary schema containing the minimum commerce tables,
two tenant scopes, products, variants, inventory transactions, COD orders, order items,
background jobs, and an `alembic_version` marker. It validates restored counts and tenant joins.
It does not replace a provider-managed production restore drill into a separate non-production
database.

## Production Deploy

```powershell
vercel pull --yes --environment=production
vercel build --prod
vercel deploy --prebuilt --prod
```

After deployment, verify health, migration head, diagnostic queue execution, browser acceptance,
and recent Vercel logs before promoting or declaring launch readiness.

Run the unauthenticated deployment smoke gate against every Preview and the final Production URL:

```powershell
uv run python scripts/verify_deployment_smoke.py https://commerce-revenue-autopilot.vercel.app
```

This checks public security headers, `/health/live`, `/health/ready`, production-hidden
`/openapi.json`, and the reserved API 404 behavior for `/api/v1/conversations`. It does not
replace authenticated API, browser, provider, worker, migration, or backup/restore acceptance.

When running the full release gate against an already deployed Preview or Production URL, include
the URL directly:

```powershell
uv run python scripts/verify_all.py `
  --migration-endpoint https://commerce-revenue-autopilot.vercel.app/api/v1/internal/release/verify-migrations `
  --release-secret-file .vercel/.cron-secret.local `
  --deployment-url https://commerce-revenue-autopilot.vercel.app
```

## Rollback

Prefer `vercel rollback` or alias promotion to the last known-good deployment when the database
schema is compatible. If schema rollback is not compatible, restore a verified backup into a new
database and update `DATABASE_URL` only after validation.
