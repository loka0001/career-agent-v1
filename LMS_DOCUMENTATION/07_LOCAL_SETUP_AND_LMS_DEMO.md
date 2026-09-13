# Local Setup and LMS Demonstration

## Safe ZIP contents

The LMS archive contains tracked project source and documentation. It intentionally excludes:

- `.git/` history and local Git configuration.
- `.env` and all real secret values.
- `.venv/`, `_uv/`, `node_modules/`, package caches, and downloaded tools.
- `dist/`, `build/`, `.next/`, `coverage/`, `htmlcov/`, and test/type/lint caches.
- Local databases, upload files, mutable screenshots, and machine-specific deployment state.

The archive includes `.env.example`, `uv.lock`, `requirements.txt`, `package-lock.json`, Docker
files, migrations, tests, design documentation, and this LMS pack so another developer can
recreate the environment.

## Prerequisites

- Windows PowerShell or an equivalent shell.
- Python 3.11, 3.12, or 3.13.
- Node.js 24.x and npm.
- `uv` for the locked Python environment.
- Docker Desktop only if using the container/PostgreSQL path.

PostgreSQL is required for production migration verification, but the isolated local demo can
use SQLite.

## First-time setup

From the extracted project root:

```powershell
uv sync --all-groups --locked
uv run python -m scripts.bootstrap_env
uv run python -m scripts.init_local
npm --prefix web ci
```

`bootstrap_env` generates fresh local secrets and prints the demo password once. Do not reuse a
password or API key from chat, source control, screenshots, or another machine.

`init_local` is idempotent for its local SQLite schema and seed data. It refuses production and
non-SQLite targets. PostgreSQL schema changes must use Alembic.

## Start the application

Open three terminal windows from the project root.

Backend API:

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm --prefix web run dev -- --host 127.0.0.1
```

Background worker:

```powershell
uv run python -m scripts.worker
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness: `http://127.0.0.1:8000/health/ready`

Production intentionally disables interactive API documentation.

## Instructor demonstration path

1. Open the landing page and demonstrate Arabic RTL, English LTR, dark/light/system theme, and
   responsive navigation.
2. Register or use the generated local demo account; explain that cookies plus CSRF secure the
   session.
3. Open Command Center and show how API data, entitlements, and operational priorities are
   composed.
4. Add a product with an image. Explain image validation, deterministic/local AI, SQL draft,
   review, activation, and search indexing.
5. Generate a marketing pack, edit it, approve it, and explain the approval version/hash.
6. Show that publishing is fake/disabled locally unless an explicitly configured provider exists.
7. Open the inbox, simulate an inbound message, request a suggestion, and discuss SQL-grounded
   retrieval and citations.
8. Create an order and apply a legal transition; inspect totals and timeline.
9. Scan opportunities and inspect evidence, expected value, and decision states.
10. Show automations, content calendar, analytics, integration health, privacy, security sessions,
    and role-limited operator screens.
11. Open Swagger and relate a UI action to its `/api/v1` request.
12. Run focused tests to show the project is executable evidence, not only UI mockups.

## Verification commands

Fast focused checks:

```powershell
uv run ruff check app scripts tests
uv run mypy app scripts
uv run pytest
npm --prefix web run lint
npm --prefix web run test:coverage
npm --prefix web run build
```

Full release verification requires a disposable PostgreSQL URL:

```powershell
$env:VERIFY_POSTGRES_URL = "<disposable PostgreSQL TLS URL>"
uv run python scripts/verify_all.py
```

The verifier creates/removes isolated schemas and must never point migration tests at a
production public schema.

## Docker path

`Dockerfile` builds the frontend and Python runtime. `docker-compose.yml` describes the local
service topology. Review environment placeholders before running and never bake `.env` or
credentials into an image.

Typical use:

```powershell
docker compose build
docker compose up
```

Database migration and worker operations remain explicit; a container build is not authorization
to mutate production data.

## Common troubleshooting

| Symptom                   | Check                                                                                              |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| Frontend cannot call API  | Confirm both processes, Vite proxy/base configuration, and allowed origin.                         |
| 401                       | Session missing, expired, revoked, or email/MFA step incomplete.                                   |
| 403 on POST/PATCH/PUT     | CSRF token, role, current membership/store, or API-key scope/origin.                               |
| 429                       | Auth/public/client rate bucket exceeded; wait for the fixed window.                                |
| 502/503 AI or integration | Live provider missing/failing; use deterministic local mode only when explicitly intended.         |
| Readiness 503             | Inspect database, search provider, and queue/worker configuration.                                 |
| Jobs remain pending       | Start worker and inspect lease/retry/operator diagnostics.                                         |
| Publishing refused        | Product/content state, validation warnings, approval hash, provider configuration, or idempotency. |
| Layout direction wrong    | Check locale context, document `lang/dir`, and logical CSS lint.                                   |
| Migration mismatch        | Compare Alembic head; do not create tables manually in production.                                 |

## Production boundary for an LMS reviewer

An instructor can assess the architecture and local behavior without any live provider secrets.
Do not upload live API keys to an LMS. If the LMS needs a demonstration, use deterministic mode,
generated local credentials, seeded data, and recorded screenshots/videos with secrets removed.
