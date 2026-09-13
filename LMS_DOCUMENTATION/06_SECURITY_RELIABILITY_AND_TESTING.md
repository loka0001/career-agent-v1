# Security, Reliability, and Testing

## Security model

Security is layered around identity, tenant isolation, untrusted input, external providers, and
high-cost or irreversible operations.

### Identity and authorization

- Passwords are scrypt-hashed; plaintext passwords are never persisted.
- Password strength is checked during registration/reset/change.
- Login is throttled by identity and aggregate IP before password verification to limit CPU
  exhaustion and distributed guessing.
- Repeated failures use progressive exponential delay instead of a permanent hard lock.
- Email verification, password reset, and invitations use expiring single-purpose tokens.
- Sessions are signed, time limited, persisted, individually revocable, HttpOnly, SameSite Lax,
  and Secure in production.
- State-changing cookie-authenticated requests require a double-submit CSRF token.
- MFA setup/confirmation/disable and session listing/revocation are available.
- RBAC is checked by backend dependencies and services.
- Last-owner protections prevent accidental organization abandonment.

### Tenant and data protection

- Every business lookup uses current store or organization scope.
- Cross-tenant tests cover customers, orders, opportunities, automations, content, team, and
  provider resources.
- Integration credentials are encrypted and API responses expose only masked status.
- API keys are random, stored as hashes, scope-limited, origin-bound where relevant, shown once,
  and revocable.
- Private media uses tenant-bound expiring signatures.
- Database, export, deletion, and retention operations preserve the tenant boundary.

### Input and transport protection

- Pydantic contracts reject extra fields and constrain important strings/lists.
- Images are checked by extension, MIME, magic bytes, size, generated storage name, and scanner
  policy.
- Webhook media/body limits are applied before unbounded buffering.
- Merchant URLs require public HTTPS, safe address resolution, and IP pinning against DNS rebinding.
- CORS uses an allowlist and explicit credentials/methods/headers.
- React escapes rendered text; no raw customer HTML path is used.
- Security response headers and request IDs are middleware responsibilities.

### External effects

- Webhooks use provider signatures and constant-time comparison.
- Provider event IDs and idempotency keys prevent duplicate effects.
- WhatsApp outbound messages require consent and honor the 24-hour service window; templates are
  required outside it.
- Publishing requires an unchanged server approval hash.
- Orders use server-calculated values; redirects do not confirm payment.
- Quotas are enforced in services before external work.
- Production adapters fail closed when configuration is absent.

### Secrets and supply chain

- `.env` is ignored and excluded from deployment and handoff archives.
- `.env.example` contains names/placeholders only.
- Pre-commit runs Gitleaks against staged content.
- The release verifier rejects secret-looking data, environment files, caches, generated state,
  and unsafe artifacts.
- Python and npm dependency audits are represented in CI/release workflows.
- The LMS ZIP is made from tracked Git content, so `.git`, `.env`, virtual environments,
  dependencies, local databases, build output, coverage, and caches are not included.

## Rate limiting

Production rate-limit buckets are stored in SQL so multiple web instances share counters. Auth
has both targeted and IP-aggregate limits. Public widget chat/events have store-wide and
per-client fingerprint/token limits. Provider/WAF throttling is still recommended as defense in
depth if the primary database is degraded.

## Reliability model

| Risk                            | Control                                                                  |
| ------------------------------- | ------------------------------------------------------------------------ |
| Repeated HTTP/provider request  | Idempotency key or persisted provider event deduplication                |
| Provider outage                 | Typed failure, bounded timeout/retry, durable job retry, circuit breaker |
| Worker crash                    | SQL lease expiry and signed stale-job recovery                           |
| Poison job                      | Maximum attempts and dead-letter state                                   |
| Partial social publish          | Independent per-platform results and `partial` lifecycle state           |
| Stale vector/index facts        | Reload identifiers from authoritative SQL                                |
| Changed content after approval  | Version/hash mismatch clears or invalidates approval                     |
| Duplicate inventory/order event | Ledger/mapping/dedup rules                                               |
| Database unavailable            | Readiness fails; production is not reported healthy                      |
| Missing provider configuration  | Explicit 503/disabled adapter rather than fake success                   |
| Unexpected production exception | Stable error envelope, request ID, redacted log, optional Sentry         |

`/health/live` proves the process responds. `/health/ready` checks dependencies such as database,
search, and job queue. Operator endpoints expose alerts, job state, webhook state, store
diagnostics, and audit evidence to an allowlisted operator.

## Privacy and governance

- Customer consent is channel scoped and audited.
- Store/customer/account exports and deletion requests are explicit workflows.
- Retention policy is stored per tenant and enforced by a durable job.
- Meta data-deletion signed requests are supported.
- Production observability must not export customer message bodies by default.
- Sentry initialization disables default PII collection.
- Backups and restore drills are release/operations concerns, not application build side effects.

## Automated testing

### Backend

The repository test inventory changes with each hardening candidate. Use `pytest --collect-only -q`
for the current count; release claims should record the dated command result rather than copying a
number into documentation. Coverage spans five levels:

| Level       | Scope                                                                                                                                                 |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit        | Domain ranking/validation/security, provider adapters, SSRF, auth backoff, config, logging, release verifiers, worker behavior                        |
| Integration | Application flows, repositories/search, rate limits, entitlements, jobs, images, Stripe contracts                                                     |
| API         | Auth, tenancy, dashboard, inbox, catalog, inventory, orders, opportunities, automations, content, integrations, privacy, team, billing, public widget |
| E2E         | Complete HTTP journeys across multiple application capabilities                                                                                       |
| Evaluation  | Grounded inference dataset and expected assistant behavior                                                                                            |

`pytest` uses strict markers. Network/live provider tests require explicit opt-in and credentials;
normal tests remain deterministic.

### Frontend

Vitest covers shared UI, theme, public/legal pages, i18n, API behavior, and feature-specific
evidence such as inbox grounding citations. Coverage gates use V8. Browser verification exercises public and authenticated
routes, both languages, desktop/tablet/mobile viewports, overflow, console errors, failed
requests, and screenshots.

### Static and release verification

- Ruff lint and formatting for Python.
- Strict mypy for `app` and `scripts`.
- ESLint, TypeScript build, Prettier, and logical CSS for the frontend.
- Alembic clean-install and upgrade-path checks against disposable PostgreSQL.
- Repository/handoff manifest hashing and secret/state scanning.
- Environment template, provider status, production access, owner action, deployment evidence,
  backup/restore, operations runbook, frontend wiring, Docker, and Trivy checks.

The release record must be regenerated from the current checkout. The required evidence is:

| Check               | Result                                                             |
| ------------------- | ------------------------------------------------------------------ |
| Backend tests       | Current full `pytest -q` output                                    |
| Frontend tests      | Current full `npm --prefix web run test` output                    |
| Frontend coverage   | Current `npm --prefix web run test:coverage` output                |
| Ruff/format         | Current lint and format-check output                               |
| Strict mypy         | Current `mypy --strict app scripts` output                         |
| Frontend lint/build | Current lint and optimized-build output                            |
| Secret/release scan | Current release-verifier output                                    |
| Browser errors      | Current `verify:journeys`, `verify:ui`, and clean-bootstrap output |
| Accessibility       | Current automated and manual accessibility evidence               |

## Residual production work

Local correctness is not provider acceptance. Before a real launch, owners must complete:

- Credentialed Meta, WhatsApp, commerce, AI, email, media/scanner, Stripe, and monitoring tests.
- A persistent production worker or approved launch-grade scheduler.
- Platform/WAF controls and alert destinations.
- Production PostgreSQL backup/restore drill into a separate non-production destination.
- Secret rotation for any credential exposed outside the approved secret store.
- Review of the current dependency advisories in the exact deployment configuration.
- Deployment smoke tests, production readiness review, and documented owner sign-off.
