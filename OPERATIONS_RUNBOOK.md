# Operations Runbook

## Release

1. Run `python scripts/verify_all.py` with `VERIFY_POSTGRES_URL` set to a disposable
   PostgreSQL server.
2. Build the immutable web/container artifact. Do not include `.env`, local databases,
   uploads, dependency trees, or provider credentials.
3. Back up production PostgreSQL and record the backup/PITR position.
4. Acquire the release migration lock and run `alembic upgrade head` as a one-off job.
5. Deploy the saved version. Deploy the independent worker from the same source revision.
6. Check `/health/live`, `/health/ready`, worker `/health/ready`, login, catalog, one COD
   order, one signed cron drain, and browser console/network errors.
7. Record revision, Alembic head, deployment URL, smoke results, and external integration
   state.

## Health And Alerts

- Web liveness: `GET /health/live`
- Web readiness: `GET /health/ready`
- Worker readiness: `GET :8081/health/ready`
- Queue/operator metrics: protected operator overview.
- Alert on readiness failure, HTTP 5xx rate, failed/dead jobs, oldest queued-job age,
  webhook signature failures, provider degradation, auth lockout spikes, AI budget
  exhaustion, and database pool errors.

Logs must retain request IDs and stable error codes while redacting tokens, cookies,
authorization headers, message PII, and connection strings.

## Job Recovery

1. Confirm the worker revision matches the web revision.
2. Inspect queued/running/failed counts and oldest age in the operator console.
3. Verify database connectivity and provider health.
4. Stale leases recover automatically when a worker starts. If web readiness reports
   `job_queue=false` before the worker is available, call
   `POST /api/v1/internal/jobs/recover-stale` with the release Bearer credential. This
   only requeues abandoned jobs; it does not execute pending customer/provider work.
5. Recheck web readiness, then start the matching worker and observe queue age/error
   metrics before allowing it to drain work.
6. Replay only dead jobs whose root cause is fixed. Replay is idempotent and audited;
   never edit job payloads or inject secrets.

## Provider Incident

1. Disable or disconnect the affected store connection.
2. Rotate the provider token and integration encryption key if exposure is suspected.
3. Reconnect, run a read-only health check, and replay only verified failed events.
4. Preserve provider event IDs, request IDs, and audit records without raw credentials.

## Rollback

Promote the previous immutable deployment only when its schema contract is compatible with
the current database. Alembic downgrades are not the default rollback. For an incompatible
change, stop writes and restore the pre-release backup into a new database, validate it,
then switch the deployment. Never run destructive restore commands against the active
database.
