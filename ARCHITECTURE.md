# Architecture

## Runtime Topology

```text
Browser / website widget
  -> Vercel React SPA + FastAPI web function
  -> PostgreSQL (authoritative application state)
  -> durable background_jobs queue
  -> independent Python worker
  -> per-store provider adapters

Signed provider webhooks -> FastAPI -> dedup record -> durable job -> worker
```

The web process does not run background jobs and request traffic is never used as a
scheduler. Vercel cron is a signed recovery drain. Time-sensitive work requires the
standalone worker. A separately signed recovery-only operation can requeue abandoned
leases without executing pending customer or provider work.

## Boundaries

- `app/api`: HTTP validation, auth dependencies, CSRF, and response contracts.
- `app/application`: use-case orchestration.
- `app/services`: tenant-scoped business rules and durable job handlers.
- `app/repositories`: persistence queries and authoritative lookups.
- `app/integrations`: replaceable provider adapters.
- `app/db/models.py` and `alembic`: schema and migration history.
- `web/src`: the single React SPA, with server-entitlement-aware routes, Arabic
  RTL/English LTR, responsive operational navigation, and no donor runtime.

## Sources Of Truth

- PostgreSQL owns prices, stock, order/payment/fulfillment states, approvals, consent,
  subscriptions, quotas, and provider-event deduplication.
- External catalog products identify their provider as source of truth; authoritative
  local edits are rejected and reconciliation is ledgered.
- Redirect pages never confirm payment. Signed webhooks own Stripe payment state.
- AI output is schema-validated and cannot override catalog, policy, consent, or payment
  facts.
- `FREE_ACCESS_MODE` controls SaaS access policy only. It reconciles an active internal
  Growth entitlement while retaining quotas, RBAC, tenant scope, CSRF, and audit. It
  does not change order payment or fulfillment state.

## Security Model

Sessions are revocable and CSRF-bound. Every protected query is store-scoped; sensitive
provider credentials are encrypted per connection. Provider webhooks use signatures,
constant-time comparison, replay protection, and idempotent jobs. Customer media is
private by default and served through tenant-bound expiring signatures.

Demo adapters require `DEMO_MODE=true`. Production settings reject insecure cookies,
SQLite, non-TLS database URLs, global merchant Meta tokens, weak application secrets, and
fake providers.

In free-access mode, billing checkout and portal creation fail explicitly and no
provider customer/subscription identifier is created. Dormant Stripe state machines
remain isolated behind provider configuration for a future approved activation.
