# Commerce Revenue Autopilot — LMS Documentation Pack

Documentation snapshot: 2026-08-23

Base implementation commit: `3812f6e`

Audience: software engineering instructor, reviewer, maintainer, or new developer

## What this project is

Commerce Revenue Autopilot is an Arabic-first, multi-tenant commerce operations SaaS. It
combines a merchant workspace, unified customer inbox, product and inventory management,
orders, customer intelligence, revenue opportunities, controlled automations, content
generation and approval, analytics, provider integrations, privacy operations, and an
operator console.

The implementation is a modular monolith:

- A React 19 + TypeScript + Vite single-page application in `web/`.
- A FastAPI + SQLAlchemy backend in `app/`.
- PostgreSQL is the production source of truth; an isolated SQLite database supports local
  learning and demonstration.
- A durable SQL job queue and a separate Python worker execute retryable background work.
- External systems are behind replaceable adapters.
- AI is constrained by structured schemas, retrieval, deterministic business rules,
  validation, cost controls, and human approval.

## Recommended reading order

1. `01_PRODUCT_AND_SYSTEM_OVERVIEW.md` — product purpose, actors, capabilities, topology,
   and architectural decisions.
2. `02_FRONTEND_ENGINEERING.md` — routes, components, state, API access, design system,
   RTL/LTR, accessibility, and frontend testing.
3. `03_BACKEND_ENGINEERING.md` — FastAPI request lifecycle, layers, persistence, jobs,
   errors, configuration, and deployment shape.
4. `04_AI_ENGINEERING.md` — provider modes, prompts, retrieval, ranking, grounding,
   safeguards, measurement, and limitations.
5. `05_DATA_INTEGRATIONS_AND_WORKFLOWS.md` — database domains, migrations, external
   adapters, webhooks, and end-to-end sequences.
6. `06_SECURITY_RELIABILITY_AND_TESTING.md` — threat controls, privacy, resilience,
   automated verification, and residual launch work.
7. `07_LOCAL_SETUP_AND_LMS_DEMO.md` — safe installation, startup, demonstration, and
   troubleshooting.
8. `08_API_CATALOG.md` — the complete API surface grouped by responsibility.
9. `09_GLOSSARY_AND_CODE_MAP.md` — terminology and a source-code navigation map.

## Current truth and historical records

This directory is the consolidated teaching description of the current code. Runtime source,
tests, migrations, `.env.example`, and generated OpenAPI remain the final technical truth.

The repository also contains historical planning and evidence files. Some record a point in
time when Git access, provider credentials, Node, or a production worker was unavailable. They
are useful audit records but are not always a statement about the current local checkout.

Useful specialist references include:

- `README.md` and `ARCHITECTURE.md` for the maintained project summary.
- `design.md` and `docs/ui/` for design implementation details.
- `docs/adr/` for architecture decision records.
- `PRODUCTION_ACTIVATION.md`, `PRODUCTION_READINESS.md`, and `OPERATIONS_RUNBOOK.md` for
  production activation and operations.
- `PRIVACY_AND_RETENTION.md`, `SECURITY_INCIDENT.md`, and `BACKUP_RESTORE.md` for governance.

## Repository scale

At the time this pack was created:

| Measure                            | Value |
| ---------------------------------- | ----: |
| Git-tracked files before this pack |   440 |
| Python files                       |   270 |
| React TSX files                    |    47 |
| Markdown files before this pack    |    60 |
| Database migrations                |    28 |
| Persisted SQLAlchemy model classes |    52 |
| OpenAPI paths                      |   141 |
| Backend test files                 |    65 |
| Backend tests                      |   261 |
| Frontend test files                |     5 |
| Frontend tests                     |    12 |

## Important honesty boundary

The product is fully runnable locally and its local automated checks pass. Real provider
operations are not considered live merely because an adapter exists. Meta, WhatsApp,
Shopify/WooCommerce, Stripe, OpenAI or an AI gateway, Resend, Cloudinary, ClamAV, Sentry, and
production infrastructure each require owner-supplied accounts, credentials, permissions, and
credentialed acceptance tests. Local deterministic adapters are deliberately labelled and
production configuration fails closed when a required provider is absent.
