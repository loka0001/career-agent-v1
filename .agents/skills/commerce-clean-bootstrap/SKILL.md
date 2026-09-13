---
name: commerce-clean-bootstrap
description: Rebuild and verify the Commerce Revenue Autopilot local demo from a clean checkout on Windows PowerShell. Use for onboarding, bootstrap regression checks, or release-readiness evidence; do not use to migrate or seed production.
---

# Commerce Clean Bootstrap

## Purpose

Prove that a fresh checkout can install, configure, seed, start, and serve the isolated local demo using only committed inputs and newly generated local secrets.

## Inputs

- A clean checkout of the canonical repository.
- Python 3.11-3.13, Node.js 24, npm, and `uv` on `PATH`.
- Free local ports 8000 and 5173.

PostgreSQL and provider credentials are not inputs to this local-demo workflow.

## Workflow

Run from the repository root in PowerShell.

1. Confirm `.env` is absent and `.env.example` exists. Do not copy credentials from another checkout.
2. Install locked dependencies:

   ```powershell
   uv sync --all-groups --locked
   npm --prefix web ci
   ```

3. Verify the committed environment contract:

   ```powershell
   uv run python -m scripts.verify_env_example
   ```

4. Generate fresh local secrets, retain the one-time demo password only for this verification session, and initialize the isolated SQLite demo:

   ```powershell
   uv run python -m scripts.bootstrap_env
   uv run python -m scripts.init_local
   ```

   Never place the generated password in source, screenshots, documentation, or reusable shell history.

5. Start three independent long-running processes:

   ```powershell
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   npm --prefix web run dev -- --host 127.0.0.1 --port 5173
   uv run python -m scripts.worker
   ```

6. Verify HTTP state:

   ```powershell
   Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/live
   Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready
   Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/
   ```

7. Keep the worker running, expose the one-time password only to the current shell, and run both browser gates:

   ```powershell
   $env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
   npm --prefix web run verify:journeys
   npm --prefix web run verify:ui
   Remove-Item Env:UI_DEMO_PASSWORD
   ```

   `verify:journeys` must prove the grounded Inbox suggestion/send and the edited,
   approved Content Studio publication through the real Vite-to-FastAPI path and independent
   worker. `verify:ui` proves the wider route, language, breakpoint, accessibility, overflow and
   browser-error matrix.
8. Stop the three processes and delete the isolated checkout only after its resolved path is confirmed to be the intended temporary directory. On Windows, an automated `Start-Process npm.cmd` wrapper can exit while its Vite `node.exe` child remains. Before deletion, require ports 8000, 5173, and 8081 to be closed. If a listener remains, resolve its owning PID and command line, verify that the command line points inside the isolated checkout, and only then stop that exact process tree.

## Expected Output

- Locked Python and frontend installs complete successfully.
- The environment verifier reports success.
- Local initialization returns `status: ready` and seeded products, policies, and conversations.
- Liveness, readiness, and frontend requests return HTTP 200.
- Browser login reaches the merchant command center.
- The sales journey adds exactly one sent reply with one or more grounding citations.
- The content journey creates one draft, saves a merchant edit, records approval, and reaches
  `published`.
- The worker remains running and processes both durable demo jobs.

## Failure Conditions

- `.env.example` is absent, ignored, contains secrets, or fails its verifier.
- `.env` already exists in the clean checkout; do not overwrite it implicitly.
- Dependency installation diverges from the lockfiles.
- Initialization selects production or a non-SQLite database.
- API, frontend, or worker exits unexpectedly.
- Readiness is not healthy, browser login fails, primary pages do not render, either journey does
  not reach its final state, or browser/network errors are detected.

## Verification

- Run the exact committed commands above, not an IDE-only shortcut.
- Preserve command exit codes and health responses as evidence.
- Browser evidence must use the real FastAPI backend through the Vite proxy.
- This proves only the isolated local demo. It does not prove PostgreSQL migrations, deployed runtime health, or live Meta/WhatsApp/OpenAI behavior.

## Related Files

- `.env.example`, `scripts/verify_env_example.py`, `scripts/bootstrap_env.py`
- `scripts/init_local.py`, `scripts/worker.py`, `app/main.py`
- `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json`
- `web/scripts/verify-core-journeys.mjs`, `web/scripts/verify-ui.mjs`
- `README.md`, `docs/OPERATIONS.md`

## Related Skills

- `commerce-repo-orientation` for architecture and ownership context.
- `vercel:agent-browser` for the required browser login and page verification.
