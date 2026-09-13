# Current Agent Handoff

Last reconciled: 2026-09-06

This file is a path-neutral handoff for the canonical Git repository. It replaces the obsolete
pre-multitenant prompt that contained drive-specific commands and copied test counts.

## Start here

1. Read the governing workspace `AGENT.md`/`AGENTS.md` files.
2. Read `docs/REPOSITORY_TRUTH_AUDIT.md`, `docs/THREAT_MODEL.md`, and
   `docs/EXECUTION_PLAN.md`.
3. Inspect `git status --short`, `git diff`, the current commit and remotes. Preserve unrelated
   user changes.
4. Use `.agents/skills/commerce-repo-orientation` when reconstructing ownership and
   `.agents/skills/commerce-clean-bootstrap` when repeating the clean boot.
5. Use `.agents/skills/commerce-ai-grounding-audit` for prompt, retrieval, ranking, citation, or
   factual-validator changes.
6. Use `.agents/skills/commerce-release-gate` for candidate, database, deployment, or production
   readiness claims.
7. Use `.agents/skills/commerce-core-sales-e2e` and `.agents/skills/commerce-content-e2e` to
   interpret the two primary browser journeys, and `.agents/skills/commerce-frontend-qa` for the
   wider route/state matrix.
8. Use `.agents/skills/commerce-handoff-sync` after milestones and before handoff.

## Repository truth

- Backend: FastAPI, Pydantic, SQLAlchemy/Alembic, SQLite demo and PostgreSQL production path.
- Frontend: the React/Vite SPA under `web/`; no second canonical frontend.
- Runtime: web/API process plus an independent persistent `scripts.worker` process.
- Security boundary: signed/revocable sessions, CSRF, RBAC and active tenant resolution per request;
  encrypted store-scoped provider credentials; signed/deduplicated webhooks.
- Business boundary: database facts beat model text; human approval evidence gates external
  content; outbound reply retries require client idempotency.
- Live status: no provider or deployment is live-verified for the current candidate in this
  workspace. Historical deployment identifiers are evidence pointers, not current acceptance.

## Clean local commands

Run from the repository root with Python 3.11-3.13, Node.js 24, npm and `uv`:

```powershell
uv sync --all-groups --locked
npm --prefix web ci
uv run python -m scripts.verify_env_example
uv run python -m scripts.bootstrap_env
uv run python -m scripts.init_local
```

Retain the generated one-time password only for the local verification session. Never put it in
source, chat, screenshots, documentation or reusable shell history.

Start independently:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
npm --prefix web run dev -- --host 127.0.0.1 --port 5173
uv run python -m scripts.worker
```

Then check `/health/live`, `/health/ready`, browser login, Inbox grounded send, and Content Studio
approval/publication. Keep the worker running while checking asynchronous status.

## Quality gates

```powershell
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run mypy --strict app scripts
uv run pytest -q
uv run pytest tests/evaluation/test_grounding_adversarial.py -q
npm --prefix web run lint
npm --prefix web run test
npm --prefix web run build
$env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
npm --prefix web run verify:journeys
npm --prefix web run verify:ui
Remove-Item Env:UI_DEMO_PASSWORD
```

Regenerate the handoff manifest only after source, tests, docs and skills are final. Its source-only
selection must retain `app/services/credential_vault.py`, related tests, and `data/seeds/**`; it must
continue excluding runtime database/uploads and credential export files. Run all readiness and
release verifiers after regeneration.

## External blockers

- No configured Git remote or immutable release SHA evidence.
- No deployment control-plane access to verify or deploy the historical Vercel project.
- Local PostgreSQL 17.10 clean/upgrade migrations and representative logical restore pass, but no
  approved managed PostgreSQL URL or provider backup destination is available.
- No credentialed Meta, WhatsApp, OpenAI, commerce, email, payment, monitoring, external storage,
  or malware-scanner acceptance inputs.
- No production persistent worker evidence or merchant sign-off.

Do not work around these blockers by inventing credentials, creating a replacement production
project, using demo results as live evidence, or committing secret values.
