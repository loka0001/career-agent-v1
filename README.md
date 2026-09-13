# Commerce Revenue Autopilot

For a complete instructor-oriented explanation of the frontend, backend, AI system,
architecture, data model, integrations, security, testing, and local demonstration, start with
[`LMS_DOCUMENTATION/00_START_HERE.md`](LMS_DOCUMENTATION/00_START_HERE.md).

Multi-tenant commerce operations SaaS for WhatsApp Business, Instagram, Facebook,
Shopify, WooCommerce, and generic websites. The product combines a unified inbox,
catalog-grounded sales assistance, social content generation and approval, customer
intelligence, orders, inventory accounting, revenue opportunities, and durable
automations.

## What Is Real

- Secure account lifecycle, MFA, team invitations, RBAC, store isolation, and onboarding.
- Per-store encrypted Meta, WhatsApp, Shopify, WooCommerce, and website connections.
- Signed and deduplicated provider webhooks with durable jobs and replay.
- Product variants, SKU and pricing metadata, source-of-truth controls, and an idempotent
  inventory ledger.
- Server-calculated orders, COD checkout, Stripe payment contracts, independent payment
  and fulfillment states, refunds/cancellations, and immutable history.
- Consent-aware website widget, private media URLs, export/deletion/retention workflows,
  and a protected operator console.
- Measured AI adapter with structured output, budget, quota, circuit breaker, and
  production fail-close behavior.

Provider functionality is only described as live after it has passed a credentialed
smoke test. Current product access is server-authoritative, free, and requires no card;
merchant order collection defaults to COD. Meta, WhatsApp, OpenAI, transactional email,
and Stripe activation require external accounts; see
[PRODUCTION_ACTIVATION.md](PRODUCTION_ACTIVATION.md).

## Local Development

Requirements: Python 3.11-3.13, Node.js 24, npm, and `uv`. PostgreSQL is required for
production migrations and the release migration gate, but not for the isolated local demo.

```powershell
uv sync --all-groups --locked
uv run python -m scripts.bootstrap_env
uv run python -m scripts.init_local
npm --prefix web ci
```

`bootstrap_env` creates fresh local secrets and prints the demo password once.
`init_local` creates and idempotently seeds a fresh SQLite development schema. It refuses
production and non-SQLite databases. Alembic remains the only production PostgreSQL
migration path.

Start all three development processes:

```powershell
uv run uvicorn app.main:app --reload --port 8000
npm --prefix web run dev -- --host 127.0.0.1
```

Run the durable worker separately:

```powershell
uv run python -m scripts.worker
```

With all three processes running, use only the one-time password from `bootstrap_env` to verify
the core merchant journeys and the broader browser matrix:

```powershell
$env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
npm --prefix web run verify:journeys
npm --prefix web run verify:calendar
npm --prefix web run verify:ui
Remove-Item Env:UI_DEMO_PASSWORD
```

Open `http://127.0.0.1:5173`. API documentation is available at
`http://127.0.0.1:8000/docs` outside production. Production disables API docs.

`web/` is the only frontend. Route modules are lazy loaded and the static donor template
was removed after its general palette/rhythm principles were translated into project-owned
tokens.

## Verification

Run the focused authoritative-data adversarial gate without external credentials:

```powershell
uv run pytest tests/evaluation/test_grounding_adversarial.py -q
```

It covers the eight commerce attack classes defined by the repository grounding-audit skill. A
deterministic pass is local evidence only; live structured-output acceptance requires approved
provider credentials and a separate recorded run.

Set `VERIFY_POSTGRES_URL` to a disposable PostgreSQL server. The commands create and remove
isolated schemas; they do not migrate the referenced database's public schema. Matching
`pg_dump` and `pg_restore` executables must be on `PATH` for the restore drill.

```powershell
$env:VERIFY_POSTGRES_URL = "<disposable PostgreSQL TLS URL for verification>"
$env:EXPECTED_MIGRATION_HEAD = "20260902_0030"
uv run python scripts/verify_backup_restore.py
uv run python scripts/verify_all.py
Remove-Item Env:EXPECTED_MIGRATION_HEAD
Remove-Item Env:VERIFY_POSTGRES_URL
```

Together these commands run a representative logical restore, Ruff, format checking, mypy, the
complete backend suite, clean and upgrade-path PostgreSQL migrations, a fresh `npm ci`, frontend
lint/tests/build, and the release secret/state scanner.

## Production

Builds never run migrations or seed data. Apply migrations in an explicit release job,
deploy the web service and independent worker, then run health and journey checks.

- [Production readiness](PRODUCTION_READINESS.md)
- [Architecture](ARCHITECTURE.md)
- [Operations runbook](OPERATIONS_RUNBOOK.md)
- [Backup and restore](BACKUP_RESTORE.md)
- [Privacy and retention](PRIVACY_AND_RETENTION.md)
- [Security incident record](SECURITY_INCIDENT.md)
- [Arabic usage guide](docs/ARABIC_USER_GUIDE.html)
- [No-payment access policy](docs/NO_PAYMENT_ACCESS.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Frontend inventory](docs/ui/frontend-inventory.md)
- [Design system](docs/ui/design-system.md)
- [Accessibility contract](docs/ui/accessibility.md)
