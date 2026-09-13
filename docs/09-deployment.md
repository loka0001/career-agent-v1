# Deployment

The authoritative deployment procedure is
[`OPERATIONS_RUNBOOK.md`](../OPERATIONS_RUNBOOK.md).

Important invariants:

- Build does not run migrations or seed.
- Production uses PostgreSQL with TLS and never falls back to SQLite.
- The web process does not execute queued jobs.
- Deploy `python -m scripts.worker` independently for real-time schedules.
- Vercel cron is a signed daily recovery drain.
- Roll back code only when schema-compatible; otherwise restore a verified pre-release
  backup into a new database.
