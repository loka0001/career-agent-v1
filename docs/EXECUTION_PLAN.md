# Commerce Revenue Autopilot Execution Plan

Last reconciled: 2026-09-06

This is the current execution ledger. Historical implementation counts and pre-multitenant notes
were removed because source, tests, and runtime evidence now supersede them.

## Evidence sources

- `docs/REPOSITORY_TRUTH_AUDIT.md` — source/test/demo/live capability truth.
- `docs/THREAT_MODEL.md` — assets, boundaries, threats, controls, and security gates.
- `PRODUCTION_READINESS.md` and `artifacts/production-readiness/` — historical deployment evidence
  plus current external blockers; not a substitute for a new deployment acceptance run.
- `.agents/skills/commerce-repo-orientation/SKILL.md` and
  `.agents/skills/commerce-clean-bootstrap/SKILL.md` — proven repeatable workflows.
- `.agents/skills/commerce-ai-grounding-audit/SKILL.md` — adversarial source-of-truth gate.
- `.agents/skills/commerce-release-gate/SKILL.md` — multi-layer release and evidence gate.
- `.agents/skills/commerce-core-sales-e2e/SKILL.md` and
  `.agents/skills/commerce-content-e2e/SKILL.md` — proven primary browser journeys.
- `.agents/skills/commerce-frontend-qa/SKILL.md` — merchant-facing route and state matrix.
- `.agents/skills/commerce-handoff-sync/SKILL.md` — source, documentation, and evidence reconciliation.

## Current plan

| Phase                                     | Status                                 | Exit evidence                                                                                                                                                                                                |
| ----------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Repository truth audit                    | Done                                   | Architecture map, capability truth table, contradictions and blockers recorded                                                                                                                               |
| Clean local bootstrap                     | Done for current pre-final candidate   | Manifest-only checkout, lockfile installs, env verifier, fresh secrets, SQLite seed, API/frontend/worker, health and browser login                                                                           |
| P0 source hardening                       | Done                                   | Environment contract, isolated settings, reply idempotency/audit, approval evidence, private media, privacy retention regressions                                                                            |
| Core sales journey                        | Done in isolated demo                  | Grounded suggestion, visible citations, reviewed idempotent send, worker delivery and audit evidence                                                                                                         |
| Adversarial AI grounding                  | Done for deterministic local candidate | Eight required customer attack classes plus hostile structured-output retry/fallback; live provider repetition remains external                                                                              |
| Core content journey                      | Done in isolated demo                  | Draft, explicit approval, immutable snapshot, worker publication and audit evidence                                                                                                                          |
| Documentation reconciliation              | Done for current local candidate       | Current truth audit, threat model, readiness, provider/access evidence, release report and handoff manifest are synchronized; external facts remain explicitly unverified                                    |
| Full quality and browser gates            | Done for current local candidate       | Ruff, format, strict mypy, backend suite, frontend lint/68 tests/coverage/build, store/brand profile persistence, core journeys, and the broad UI verifier including P0 navigation plus all required isolated non-happy-path states are green |
| Reference-driven productization | Inbox and catalog creation/inventory checkpoints verified; wider productization partial | Eight candidates considered, seven evidence-backed scores; public Gorgias screenshot inspected. Real bilingual catalog review/activation/onboarding/demo publication and variant ledger adjustments verified; Inbox races/context corrected. Content approval/recovery and later surfaces remain. |
| Manifest and release evidence             | Done for current local candidate       | Deterministic manifest and all local artifact/release verifiers are green                                                                                                                                    |
| Final clean-checkout repetition           | Done for current local candidate       | Source-only manifest checkout retained security-named source and seed inputs; documented bootstrap and primary browser journeys passed; repeat against the immutable release SHA before production promotion |
| Local PostgreSQL migration and restore    | Done for current local candidate       | PostgreSQL 17.10 clean and `0024 → head` migrations plus representative `pg_dump`/`pg_restore` commerce validation                                                                                           |
| Managed PostgreSQL and production release | Blocked externally                     | Approved managed database/backup destination, release SHA/remote, deployment access, independent worker and deployed smoke                                                                                   |
| Live provider acceptance                  | Blocked externally                     | Credentialed Meta, WhatsApp, OpenAI, commerce, email/storage/monitoring evidence and merchant sign-off                                                                                                       |

## Current implementation truth

- The backend is FastAPI with SQLAlchemy, Alembic, store-scoped repositories, first-party auth,
  encrypted per-store provider connections, and a database-backed worker queue.
- The only frontend is the React/Vite SPA in `web/`; it provides Arabic RTL/English LTR, light/dark
  modes, responsive operational routes, and real API wiring.
- SQLite plus deterministic/demo adapters are for isolated local use. Production requires
  PostgreSQL with TLS, separate web/worker processes, secure configuration, and credentialed
  provider acceptance.
- Price, stock, policy, approval, tenant and idempotency decisions remain server-authoritative.
- An implemented adapter is never classified as live without a dated credentialed result.

## Required final local gates

```powershell
uv sync --all-groups --locked
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run mypy --strict app scripts
uv run pytest -q
uv run pytest tests/evaluation/test_grounding_adversarial.py -q

npm --prefix web ci
npm --prefix web run lint
npm --prefix web run test
npm --prefix web run test:coverage
npm --prefix web run build
$env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
npm --prefix web run verify:journeys
npm --prefix web run verify:ui
Remove-Item Env:UI_DEMO_PASSWORD
```

After the file set is final, regenerate and verify the repository handoff manifest, rerun the
readiness/release verifiers, then repeat the clean-checkout bootstrap and browser journeys.

## Production exit criteria

Production is not complete until all of the following are evidenced against one immutable release
SHA:

1. clean and upgrade-path PostgreSQL migrations reach the candidate head and a separate restore
   drill passes;
2. web and persistent worker processes are healthy with monitoring and alert delivery;
3. public deployment smoke and authenticated merchant acceptance pass;
4. each claimed live provider passes its own inbound/outbound or publish acceptance flow;
5. privacy, session revocation, operator access, credential rotation, rollback and incident drills
   pass;
6. merchant acceptance is recorded without secrets or customer message bodies.
