# Production Operations

Last reviewed: 2026-08-01

Production URL: `https://commerce-revenue-autopilot.vercel.app`

Vercel team/project: `malek-virtz` / `commerce-revenue-autopilot`

## Daily Checks

Run:

```powershell
curl.exe -sS https://commerce-revenue-autopilot.vercel.app/health/live
curl.exe -sS https://commerce-revenue-autopilot.vercel.app/health/ready
```

Expected: HTTP 200, live `process=true`, ready `database=true`, `search=true`, and
`job_queue=true`.

For a fuller unauthenticated smoke after a Preview or Production deployment:

```powershell
uv run python scripts/verify_deployment_smoke.py https://commerce-revenue-autopilot.vercel.app
```

The smoke also verifies production security headers and fail-closed JSON 404 behavior for reserved
routes that must not fall through to the frontend.

## Queue And Scheduler

Production currently uses the signed Vercel Cron drain endpoint as a daily recovery drain:

```powershell
$secret = Get-Content -Raw '.vercel/.cron-secret.local'
curl.exe -sS -H "Authorization: Bearer $($secret.Trim())" `
  'https://commerce-revenue-autopilot.vercel.app/api/v1/internal/jobs/drain?limit=100'
```

The same endpoint recovers stale leases before executing due work. Dead-lettered jobs are visible to
configured operators at `/api/v1/operator/jobs?status=dead`.

The current Vercel account rejected a five-minute cron schedule because Hobby accounts are limited
to daily cron jobs. Launch-grade scheduling requires either a Pro-or-higher Vercel plan with a
frequent cron, or an external persistent worker running `scripts.worker`.

Use the standalone worker on a persistent runtime:

```powershell
Set-Item Env:APP_ENV production
Set-Item Env:ENABLE_BACKGROUND_WORKER true
Set-Item Env:SERVERLESS_MODE false
uv run python -m scripts.worker
```

In production, `scripts.worker` performs a startup preflight before opening the database pool. It
fails closed unless `ENABLE_BACKGROUND_WORKER=true`, the runtime is not serverless
(`SERVERLESS_MODE`/`VERCEL` false), and the database URL is PostgreSQL. These checks are redacted
and do not log secrets.

Worker health endpoints:

- `GET /health/live` returns HTTP 200 while the worker process is alive.
- `GET /health/ready` returns HTTP 200 only after the worker loop has completed a fresh
  successful poll; it returns HTTP 503 when the worker has not yet polled, has a stale poll
  heartbeat, or the last iteration failed.

The health payload includes queue metrics, start time, last poll time, last successful poll time,
and a redacted error code. It must not expose job payloads, raw exception text, credentials, or
customer messages.

## Diagnostic Job

Use only with the internal cron/release credential.

```powershell
$marker = "ops-" + (Get-Date -Format yyyyMMddHHmmss)
$secret = (Get-Content -Raw '.vercel/.cron-secret.local').Trim()
curl.exe -sS -X POST -H "Authorization: Bearer $secret" `
  "https://commerce-revenue-autopilot.vercel.app/api/v1/internal/jobs/diagnostics?scenario=success&marker=$marker"
curl.exe -sS -H "Authorization: Bearer $secret" `
  'https://commerce-revenue-autopilot.vercel.app/api/v1/internal/jobs/drain?limit=100'
curl.exe -sS -H "Authorization: Bearer $secret" `
  "https://commerce-revenue-autopilot.vercel.app/api/v1/internal/jobs/diagnostics?marker=$marker"
```

Expected: the diagnostic job reaches `succeeded`. For retry testing, use
`scenario=retry_once`, run drain once, wait at least 30 seconds, then run drain again.

## Logs

```powershell
vercel logs dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx --since 1h
```

No passwords, bearer tokens, cookies, authorization headers, complete customer messages, payment
data, or raw provider secrets may be logged.

## Alerts

Operators can inspect current in-app alert state from the protected operator console or directly:

```powershell
curl.exe -sS https://commerce-revenue-autopilot.vercel.app/api/v1/operator/alerts
```

The endpoint is session-authenticated, returns only aggregated signal state, and does not expose
job payloads, raw errors, customer messages, tokens, or provider secrets.

Minimum production alerts:

- `/health/ready` non-200 for 2 consecutive checks.
- Any unexplained HTTP 5xx burst.
- Queue `failed > 0`.
- Queue `oldest_job_age_seconds > 900`.
- Worker or scheduler no successful drain for 15 minutes.
- Provider webhook failures.
- Database backup or restore drill failure.

Implemented in-app alert checks:

- Dead-lettered jobs.
- Queued-job age above 900 seconds.
- Stale running job leases.
- Provider connections in degraded, expired, or action-required states.
- Production configuration readiness gaps, reported as stable redacted issue codes.
- Missing explicit persistent worker activation as `worker_runtime_missing`.

External alert delivery is still pending an approved destination such as Sentry, a Vercel log drain,
Slack, email, or another owner-approved incident channel.

Production startup logs also emit redacted `production_readiness_incomplete` warnings when
operations prerequisites are missing, including operator access allowlist, external error
monitoring, release SHA, cron authentication, integration encryption, transactional email, Meta,
WhatsApp, AI, media, or malware-scanning configuration.
