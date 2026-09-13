---
name: commerce-repo-orientation
description: Reconstruct the Commerce Revenue Autopilot architecture, critical flows, and changed-since-baseline notes. Use for repository onboarding, truth audits, architecture reviews, or after broad structural changes; do not use for a narrow edit whose owning component is already known.
---

# Commerce Repository Orientation

## Purpose

Produce an evidence-backed map of the current system without treating documentation or adapter presence as runtime proof.

## Inputs

- The canonical Git repository root.
- An optional baseline commit or prior architecture map for change comparison.
- The scope requested by the user; default to the full repository only for onboarding or truth-audit work.

## Workflow

1. Resolve the repository root with `git rev-parse --show-toplevel`; inspect `git status --short`, the current commit, and governing `AGENT.md`/`AGENTS.md` files in the workspace hierarchy.
2. Inventory files with `rg --files`. Read bootstrap and composition first: `app/main.py`, `app/config.py`, `app/container.py`, `app/api/router.py`, `scripts/worker.py`, `pyproject.toml`, and `web/package.json`.
3. Trace backend ownership from `app/api/routes/` through `app/application/` or `app/services/`, then `app/repositories/`, `app/db/`, and `alembic/versions/`. Confirm transaction, tenant, idempotency, and approval boundaries in source rather than inferring them from names.
4. Trace external behavior through `app/integrations/`, provider connection storage, webhook routes, the durable job queue, and worker handlers. Label adapters as implemented, demo-verified, or live-verified separately.
5. Trace the browser path from `web/src/main.tsx` and app routing through `web/src/lib/api.ts`, feature pages, shared types, and relevant tests.
6. Map tests to each critical capability. A code path with no meaningful test is not test-verified; a test without browser/runtime evidence is not demo-verified.
7. Compare the baseline with `git diff --name-status <baseline>...HEAD` plus working-tree changes when a baseline is supplied. Describe architectural effects, not just filenames.
8. Reconcile source, tests, runtime evidence, and docs. Record contradictions explicitly and use the strongest available evidence as the current truth.

## Expected Output

- A compact component map with ownership and trust boundaries.
- Critical flows for authentication/tenant resolution, inbound and outbound messaging, grounded AI sales assistance, content approval/publishing, provider webhooks, and worker execution.
- Changed-since-baseline notes.
- A capability table that keeps `code exists`, `test exists`, `demo verified`, and `live verified` as independent facts.
- Blockers and unverified assumptions with source paths or commands that support them.

## Failure Conditions

- The canonical repository or governing instructions cannot be resolved.
- A requested comparison has no identifiable baseline.
- Documentation conflicts with source or runtime evidence. Do not choose silently; report the conflict.
- Live credentials or deployment access are absent. Mark live status unverified instead of promoting adapter/test evidence.

## Verification

- Every mapped component is backed by a real path.
- Each critical flow reaches its persistence or provider boundary and returns to its user-visible result.
- Test, local-demo, and live-production claims are kept distinct.
- Working-tree changes and the selected baseline are stated in the output.

## Related Files

- `app/main.py`, `app/config.py`, `app/container.py`, `app/api/router.py`
- `app/api/routes/`, `app/application/`, `app/services/`, `app/repositories/`
- `app/db/`, `alembic/versions/`, `app/integrations/`, `scripts/worker.py`
- `web/src/lib/api.ts`, `web/src/features/`, `tests/`, `docs/`, `LMS_DOCUMENTATION/`

## Related Skills

- `commerce-clean-bootstrap` for clean runtime proof.
- `codex-security:threat-model` when the requested map must include a formal threat model.

