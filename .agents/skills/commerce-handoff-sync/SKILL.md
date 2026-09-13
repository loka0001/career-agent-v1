---
name: commerce-handoff-sync
description: Reconcile Commerce Revenue Autopilot source truth with README, implementation status, production readiness, LMS docs, deployment instructions, provider evidence, and the deterministic handoff manifest. Use after major milestones or before handoff/release to remove stale commands, URLs, credentials, counts, architecture claims, and overstatements.
---

# Commerce Handoff Sync

## Purpose

Prevent source, operational documentation, evidence artifacts, and release claims from drifting.

## When To Use

- After a major feature, migration, architecture, provider, test, deployment, or release-process
  change.
- Before handing the candidate to another agent, reviewer, CI system, or operator.

## When Not To Use

- Do not rewrite historical evidence as if it described the current candidate.
- Do not invent deployment, provider, backup, merchant, or production acceptance.
- Do not put credentials, secret values, customer payloads, or reusable passwords into artifacts.

## Inputs

- The actual working tree and Git state.
- Current source, migration heads, tests, workflows, runtime scripts, and verified command outputs.
- README, status/readiness reports, LMS documentation, deployment/runbook documents, and agent
  evidence JSON.

## Workflow

1. Establish source truth:

   ```powershell
   git status --short
   git diff --check
   uv run alembic heads
   ```

   Record the real branch, SHA, dirty state, remote availability, migration head, architecture, and
   provider boundaries.
2. Compare the source truth against:
   - `README.md`, `IMPLEMENTATION_STATUS.md`, `PRODUCTION_READINESS.md`, `FINAL_REPORT.md`;
   - `docs/01-current-state.md`, release/deployment/operations/backup/incident docs;
   - relevant `LMS_DOCUMENTATION/` files;
   - `artifacts/agent/current-state.json`, `provider-status.json`, and production-readiness evidence.
3. Search globally for superseded migration IDs, deployment IDs/URLs, commands, credentials,
   numeric test counts, architecture labels, provider states, and production-ready language.
   Classify each occurrence as current, historical, blocked, or stale before editing.
4. Update claims from direct evidence. Separate local, preview, production, managed-database,
   provider, and merchant acceptance. Keep blockers and exact owner actions intact.
5. Validate JSON, regenerate the manifest only after all stable files are final, and run:

   ```powershell
   uv run python scripts/verify_provider_status.py
   uv run python scripts/verify_environment_matrix.py
   uv run python scripts/verify_owner_actions.py
   uv run python scripts/verify_production_access.py
   uv run python scripts/verify_vercel_access_evidence.py
   uv run python scripts/verify_operations_runbook.py
   uv run python scripts/verify_repository_handoff_manifest.py --write
   uv run python scripts/verify_repository_handoff_manifest.py
   uv run python scripts/verify_readiness_artifacts.py
   ```

6. Run `commerce-release-gate` from a relocated source-only checkout before the final handoff.

## Expected Output

- Commands, URLs, IDs, migration head, architecture, provider states, and verification dates agree
  with source or are explicitly labelled historical.
- No reusable credential, secret-looking value, unsupported test count, or overclaim remains.
- Readiness begins with `Not production ready` while any blocker remains.
- Agent JSON, owner actions, manifest, readiness verifier, and relocated release scan pass.

## Failure Conditions

- Documentation claims behavior not present in source or acceptance not directly observed.
- Current-candidate and historical production evidence are merged.
- A required blocker, owner action, provider status, or evidence timestamp disappears.
- The manifest includes secrets, caches, build output, databases, logs, dependencies, mutable agent
  state, or temporary workspaces.
- Evidence changes make the manifest stale.

## Verification

- Preserve the exact dated commands that support each updated claim.
- Prefer no numeric test count unless copied from the same final run; otherwise state the suite
  passed.
- Finish with `git diff --check`, manifest validation, readiness validation, and a source-only
  release scan.

## Related Files

- `README.md`, `IMPLEMENTATION_STATUS.md`, `PRODUCTION_READINESS.md`, `FINAL_REPORT.md`
- `docs/REPOSITORY_TRUTH_AUDIT.md`, `docs/EXECUTION_PLAN.md`, `docs/AGENT_HANDOFF_PROMPT.md`
- `docs/RELEASE_PROCESS.md`, `docs/OPERATIONS.md`, `docs/BACKUP_AND_RESTORE.md`
- `LMS_DOCUMENTATION/`
- `artifacts/agent/`, `artifacts/production-readiness/`
- `scripts/verify_*`

## Related Skills

- `commerce-repo-orientation`
- `commerce-release-gate`
