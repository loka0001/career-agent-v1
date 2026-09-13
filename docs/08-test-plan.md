# Automated Test Plan

## What “test the APIs” means

An API test behaves like a client: it sends an HTTP request, then checks the HTTP status, safe JSON contract, cookie/header rules, and persistent state. It proves more than calling a Python function because routing, validation, authentication, dependencies, error mapping, and serialization run together.

## Test layers

| Layer       | Location              | Main evidence                                                                                                                                                                     |
| ----------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit        | `tests/unit`          | Files, feature merge, money filters, ranking, marketing/reply validators, sessions, Meta error/poll bounds.                                                                       |
| Integration | `tests/integration`   | SQL repositories, Chroma, seeded policies/products, sales application flow.                                                                                                       |
| API         | `tests/api`           | Every route family, auth, CSRF, invalid multipart, approval, idempotency, safe errors.                                                                                            |
| E2E         | `tests/e2e`           | Existing merchant journeys plus a complete new-tenant commerce journey across Meta demo, orders, opportunities, automation, content, analytics, and isolation.                    |
| Inference   | `tests/evaluation`    | 15 normal Arabic/English cases plus 8 adversarial commerce vectors; intent, ambiguity, source-of-truth price/stock, budget, top-3, citation, injection, and fallback constraints. |
| Frontend    | `web/src/**/*.test.*` | Shared accessible states, fetch/CSRF behavior, expired-session propagation, login recovery notice, feature/operator denial, and localized provider/publication status presentation. |

## Commands

```powershell
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run mypy --strict app scripts
uv run pytest -q

# Focused AI grounding gate
uv run pytest tests/evaluation/test_grounding_adversarial.py tests/unit/test_validators.py tests/evaluation/test_inference_dataset.py tests/api/test_sales.py tests/integration/test_application_flows.py -q

npm --prefix web run lint
npm --prefix web run test
npm --prefix web run test:coverage
npm --prefix web run build
$env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
npm --prefix web run verify:journeys
npm --prefix web run verify:calendar
npm --prefix web run verify:ui
Remove-Item Env:UI_DEMO_PASSWORD

# On an explicitly disposable PostgreSQL server with matching client tools on PATH
$env:VERIFY_POSTGRES_URL = Read-Host "Disposable PostgreSQL URL"
$env:EXPECTED_MIGRATION_HEAD = "20260902_0030"
uv run python -c "from scripts.verify_all import migration_gate; import os; migration_gate(os.environ['VERIFY_POSTGRES_URL'])"
uv run python scripts/verify_backup_restore.py
Remove-Item Env:EXPECTED_MIGRATION_HEAD
Remove-Item Env:VERIFY_POSTGRES_URL
```

## Current regression baseline

Do not copy a numeric test count into release claims. Run the commands above and record their dated
output in the release evidence. `verify:journeys` covers login; bilingual store- and brand-profile
save/reload checks that restore their original values; a citation-grounded Inbox send with exactly
one recorded outbound message; and Content Studio generation, merchant edit, approval and worker
publication. It polls the exact server-side entities before checking their rendered terminal state.
`verify:calendar` creates four future, unapproved drafts in the isolated demo. It checks month-end
navigation, agenda ranges, filters, review/campaign links, Arabic/English responsive layouts, and
explicit API timezone offsets with noon remaining noon after reload in Africa/Cairo.
`verify:ui` remains the broader desktop/mobile, dark/light, overflow, request, console, and
page-error gate. It explicitly exercises isolated loading, empty, network-unavailable,
provider-disconnected, AI-unavailable, publish-failed, Home partial-source failure, feature-denied,
and expired-session states; the interceptions do not mutate live or provider data. The Home check
also verifies actionable English labels and rejects the removed unbacked notification control.
It asserts the exact six-link desktop P0 navigation, expandable secondary access, hidden dormant
Billing link during free access, and the four P0 mobile destinations plus More.

- The adversarial grounding dataset covers nonexistent and out-of-stock products, ambiguous needs,
  fake discounts, unknown shipping details, prompt injection, database overrides, and contradictory
  requests. Hostile model-output tests separately prove retry and deterministic fallback.
- The database gate separately proves a clean migration, an upgrade from the documented prior
  revision, and a logical dump/drop/restore of representative multi-tenant commerce records.
- The end-to-end new-tenant journey registers a store, selects a plan, activates a product,
  connects Demo Meta, ingests a signed webhook, produces a grounded recommendation, creates a
  draft order, processes an opportunity, runs an automation, generates/approves/publishes content,
  reads analytics, and verifies tenant isolation.

## Adding one API test

1. Use the `context` fixture from `tests/conftest.py`.
2. Call `context.login()` for authenticated routes and use the returned CSRF header.
3. Send a request through `context.client`.
4. Assert the exact status and business result.
5. Add at least one invalid-state assertion.
6. Re-run the smallest test file, then the full suite.

## Live test policy

- CI never needs OpenAI, Cloudinary, or Meta keys.
- `RUN_LIVE_AI_EVALS` and `RUN_META_SMOKE_TESTS` default to false.
- The Meta smoke script performs read-only connection checks and requires explicit confirmation.
- Creating a real post is a manual acceptance test after a human approves the exact content.
- Demo tests never spend money, send a real message, or publish to a real account.
