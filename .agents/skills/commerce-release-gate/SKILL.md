---
name: commerce-release-gate
description: Run and interpret the Commerce Revenue Autopilot release gates across source quality, PostgreSQL migrations and restore, browser journeys, immutable Git evidence, deployment smoke, and provider readiness. Use for release candidates or production-readiness claims; do not promote local/demo results to live acceptance.
---

# Commerce Release Gate

## Purpose

Block release unless one candidate passes the required source, database, runtime, browser, security,
and evidence checks at the scope being claimed.

## When To Use

- Before calling a working tree, commit, preview, or production deployment release-ready.
- After migrations, worker/provider boundaries, core journeys, environment contracts, or release
  scripts change.
- When reconciling which checks are locally proven and which still require external access.

## When Not To Use

- Do not use a dirty local worktree as immutable release evidence.
- Do not run migration or restore drills against production or a database that is not explicitly
  disposable.
- Do not treat deterministic/demo adapters, local PostgreSQL, or adapter tests as credentialed
  provider, managed-database, deployed-worker, or merchant acceptance.

## Inputs

- The exact candidate tree and, for final release, its immutable Git SHA and configured remote.
- Python 3.11-3.13, Node.js 24, npm, `uv`, and locked project dependencies.
- `VERIFY_POSTGRES_URL` for a disposable PostgreSQL server that permits temporary schemas.
- PostgreSQL `pg_dump` and `pg_restore` matching the server major for the restore drill.
- The one-time local demo password only for browser gates.
- Deployment URL, provider credentials, and operator authorization only for the corresponding
  external acceptance stage.

## Workflow

1. Inspect `git status`, `git diff`, migration heads, provider evidence, and the current truth
   audit. Preserve unrelated user changes and reject secret or local-state files.
2. Run source and application gates:

   ```powershell
   uv run ruff check app tests scripts
   uv run ruff format --check app tests scripts
   uv run mypy --strict app scripts
   uv run pytest -p no:cacheprovider -q
   npm --prefix web run lint
   npm --prefix web run test
   npm --prefix web run build
   npm --prefix web run format:check
   ```

3. Against a disposable PostgreSQL server, run both migration paths and the representative restore
   drill. Never point these variables at production:

   ```powershell
   $env:VERIFY_POSTGRES_URL = Read-Host "Disposable PostgreSQL URL"
   $env:EXPECTED_MIGRATION_HEAD = "20260902_0030"
   uv run python -c "from scripts.verify_all import migration_gate; import os; migration_gate(os.environ['VERIFY_POSTGRES_URL'])"
   uv run python scripts/verify_backup_restore.py
   Remove-Item Env:EXPECTED_MIGRATION_HEAD
   Remove-Item Env:VERIFY_POSTGRES_URL
   ```

   The migration gate must create and remove isolated `verify_empty_*` and `verify_upgrade_*`
   schemas. The restore gate must dump, drop, restore, validate representative commerce rows and
   tenant joins, and remove its `verify_backup_*` schema.
4. Repeat the clean bootstrap and both browser gates through the real API and independent worker by
   following `commerce-clean-bootstrap`.
5. Finalize the file set, regenerate the handoff manifest, then run every readiness verifier and
   the release source scanner from a relocated source-only checkout.
6. For an actual release, run `scripts/verify_all.py` against the immutable SHA with the disposable
   PostgreSQL URL. Add `--deployment-url` after deploying the same SHA. Record external provider,
   persistent-worker, restore, rollback, and merchant acceptance separately.

## Expected Output

- Quality, backend, frontend, browser, worker, evidence, and source-hygiene gates pass.
- Clean PostgreSQL migration and prior-version upgrade both reach the documented head.
- `pg_dump`/`pg_restore` preserves migration version, representative catalog/inventory/orders/jobs,
  counts, totals, and tenant relationships.
- The handoff manifest matches the final source-only candidate.
- Final release evidence names one immutable SHA and clearly separates local, preview, production,
  and provider-specific results.

## Failure Conditions

- Any check is skipped, weakened, or rerun against a different candidate without disclosure.
- Alembic uses `public` when a disposable verifier schema was intended, or accepts an arbitrary
  migration schema name.
- A developer `.env` changes migration behavior, or a percent-encoded database URL breaks Alembic.
- Dump/restore tools are missing, version-incompatible, or restore validation loses rows or tenant
  relationships.
- Source-only release scanning finds secrets, `.env`, databases, caches, logs, dependencies, or
  binary build state.
- Local/demo success is represented as managed PostgreSQL, deployment, worker, provider, or merchant
  acceptance.

## Verification

- Preserve exact commands, dates, versions, candidate SHA, and safe external request/deployment IDs.
- Confirm disposable schemas are absent after both successful and failed database runs.
- Run `scripts/verify_repository_handoff_manifest.py` and
  `scripts/verify_readiness_artifacts.py` after every final evidence change.
- A production-ready claim requires all external blockers in `docs/REPOSITORY_TRUTH_AUDIT.md` to be
  closed with direct evidence.

## Related Files

- `scripts/verify_all.py`, `scripts/verify_backup_restore.py`, `scripts/verify_release.py`
- `scripts/verify_repository_handoff_manifest.py`, `scripts/verify_readiness_artifacts.py`
- `alembic/env.py`, `alembic/versions/`, `app/db/session.py`
- `docs/RELEASE_PROCESS.md`, `docs/REPOSITORY_TRUTH_AUDIT.md`, `FINAL_REPORT.md`
- `artifacts/agent/current-state.json`, `artifacts/agent/provider-status.json`

## Related Skills

- `commerce-clean-bootstrap` for the isolated runtime and browser gates.
- `commerce-ai-grounding-audit` for adversarial sales-assistant acceptance.
- `commerce-repo-orientation` for architecture and ownership context.
