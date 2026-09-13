# Demo Script Index

Last verified: 2026-07-30

The complete local, isolated demonstration sequence is in `docs/DEMO_SCRIPT.md`.

Demo mode is only for local or explicitly isolated environments:

```powershell
uv run python -m scripts.bootstrap_env
uv run python -m scripts.init_local
uv run uvicorn app.main:app --port 8000
npm --prefix web ci
npm --prefix web run dev -- --host 127.0.0.1
```

Use the one-time password printed by `bootstrap_env`; do not copy a Demo credential
into production. The production deployment runs with `DEMO_MODE=false`, fake
publishing disabled, real provider publishing gated by credentials, and COD for
merchant order collection.

During a Demo, distinguish clearly between:

- internal functionality that works now;
- isolated Demo data or adapters;
- provider-dependent capabilities awaiting configuration;
- unavailable external capabilities.

Never describe Demo publishing, seeded data, or deterministic AI as a credentialed
live provider result.

