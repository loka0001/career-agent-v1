# Glossary and Code Map

## Glossary

| Term                   | Meaning in this project                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| Modular monolith       | One backend deployment with enforced internal module boundaries and one database transaction boundary. |
| Tenant                 | A store/organization security boundary; one user can have memberships in multiple stores.              |
| Composition root       | `app/container.py`, where concrete repositories and providers are selected and wired.                  |
| Source of truth        | The authoritative record used for a decision; usually SQL, never an LLM response.                      |
| Domain contract        | Strict Pydantic model representing a valid business input/output independent of HTTP or SQL.           |
| Repository             | Tenant-aware persistence adapter translating SQLAlchemy rows to domain records.                        |
| Provider adapter       | Replaceable implementation for AI, social, commerce, payment, email, media, or scanning.               |
| Deterministic provider | Local/test implementation with stable behavior and no external side effect.                            |
| Disabled provider      | Production safety adapter that fails explicitly when live configuration is absent.                     |
| Grounding              | Restricting an AI response to supplied authoritative products/policies and validated citations.        |
| Retrieval              | Finding candidate product IDs or policy references using lexical/hash/vector similarity.               |
| Approval hash          | SHA-256 evidence binding approved text, hashtags, and version to one human decision.                   |
| Idempotency            | Repeating the same request/event without repeating its business side effect.                           |
| Durable job            | SQL-persisted background work with deduplication, lease, retry, and terminal state.                    |
| Lease                  | Temporary ownership of a job by one worker; expiry permits recovery after a crash.                     |
| Dead letter            | Job state after maximum attempts, requiring operator review/replay.                                    |
| CSRF                   | Protection requiring a token in addition to cookie session credentials for state changes.              |
| RBAC                   | Server-enforced role-based access control.                                                             |
| RFM                    | Customer recency, frequency, and monetary-value intelligence.                                          |
| COD                    | Cash on delivery; an order collection method independent of SaaS subscription billing.                 |
| Entitlement            | Server-authoritative feature access based on current subscription/free-access policy.                  |
| Free access mode       | SaaS access policy that grants an internal entitlement without creating payment state.                 |
| Provider activation    | External adapter exists, but real credentials/review/smoke tests are still required.                   |
| Fail closed            | Missing/invalid security or provider configuration blocks the action rather than using a fake success. |

## Backend code map

| Path                        | Read this to understand                                                |
| --------------------------- | ---------------------------------------------------------------------- |
| `app/main.py`               | FastAPI construction, middleware, routers, static SPA/media serving    |
| `app/config.py`             | Environment contract and production readiness validation               |
| `app/container.py`          | Concrete dependency wiring and runtime-mode selection                  |
| `app/security.py`           | Authentication, request-integrity, and signed-resource utilities       |
| `app/api/dependencies.py`   | Current user/store, role, API key, operator, and database dependencies |
| `app/api/error_handlers.py` | Domain-to-HTTP error mapping                                           |
| `app/api/routes/`           | Public HTTP interface grouped by capability                            |
| `app/application/`          | Product, marketing, and grounded-assistant use cases                   |
| `app/domain/enums.py`       | Business lifecycle values                                              |
| `app/domain/errors.py`      | Stable business failure taxonomy                                       |
| `app/domain/model_groups/`  | Strict business contracts by domain                                    |
| `app/domain/ranking.py`     | Deterministic recommendation filters and scores                        |
| `app/domain/validators.py`  | Image, content, approval, and grounding validation                     |
| `app/services/`             | Operational business rules and background handlers                     |
| `app/repositories/`         | Tenant-aware SQL persistence boundaries                                |
| `app/integrations/`         | AI/provider/storage/payment/search implementations                     |
| `app/db/model_groups/`      | SQLAlchemy schema grouped by domain                                    |
| `alembic/versions/`         | Ordered production schema evolution                                    |
| `scripts/worker.py`         | Independent durable worker entry point                                 |

## Frontend code map

| Path                             | Read this to understand                                             |
| -------------------------------- | ------------------------------------------------------------------- |
| `web/src/main.tsx`               | React bootstrapping and global providers/styles                     |
| `web/src/app/App.tsx`            | Complete route tree and lazy feature loading                        |
| `web/src/app/AuthContext.tsx`    | Session/current store/CSRF frontend state                           |
| `web/src/app/ProtectedRoute.tsx` | Authentication, entitlement, and operator route guards              |
| `web/src/app/AppShell.tsx`       | Sidebar, top bar, mobile nav, locale/theme/profile/command surfaces |
| `web/src/app/ThemeContext.tsx`   | Dark/light/system behavior                                          |
| `web/src/components/ui/`         | Shared design-system primitives                                     |
| `web/src/features/`              | Page-level capabilities                                             |
| `web/src/i18n/`                  | Arabic/English dictionaries and document direction                  |
| `web/src/lib/api.ts`             | Cookie/CSRF-aware typed HTTP client                                 |
| `web/src/lib/types.ts`           | Frontend view of backend contracts                                  |
| `web/src/styles/tokens.css`      | Design tokens                                                       |
| `web/src/styles/*.css`           | Shell, commerce, operations, and public responsive layouts          |
| `web/scripts/verify-ui.mjs`      | Browser verification scenario                                       |

## Test code map

| Path                      | Focus                                                                        |
| ------------------------- | ---------------------------------------------------------------------------- |
| `tests/unit/`             | Pure rules, security utilities, config, adapters, verifiers, worker          |
| `tests/integration/`      | Repository, search, job, rate-limit, billing, image, application integration |
| `tests/api/`              | HTTP contracts, auth, tenant isolation, and all API capability families      |
| `tests/e2e/`              | Complete cross-module application journeys                                   |
| `tests/evaluation/`       | Grounded assistant evaluation dataset                                        |
| `web/src/**/*.test.tsx`   | Components, contexts, legal pages, i18n                                      |
| `web/src/lib/api.test.ts` | API-client behavior                                                          |

## Operations and governance map

| Path                                            | Purpose                                             |
| ----------------------------------------------- | --------------------------------------------------- |
| `README.md`                                     | Maintained quick start and high-level product truth |
| `ARCHITECTURE.md`                               | Concise runtime topology and invariants             |
| `design.md`                                     | Detailed frontend product/design specification      |
| `docs/adr/`                                     | Architectural decision records                      |
| `OPERATIONS_RUNBOOK.md`                         | Production operation and recovery                   |
| `BACKUP_RESTORE.md`                             | Backup/restore contract                             |
| `PRIVACY_AND_RETENTION.md`                      | Data lifecycle policy                               |
| `PRODUCTION_ACTIVATION.md`                      | Provider and infrastructure activation              |
| `PRODUCTION_READINESS.md`                       | Honest launch checklist                             |
| `.github/workflows/`                            | CI gates                                            |
| `.pre-commit-config.yaml`                       | Local Gitleaks protection                           |
| `scripts/verify_all.py`                         | Full verification orchestrator                      |
| `scripts/verify_release.py`                     | Release-source safety scanner                       |
| `scripts/verify_repository_handoff_manifest.py` | Deterministic source/document handoff hashes        |

## Suggested learning questions

1. Why is the LLM not allowed to be the orchestration layer?
2. Why does retrieval return identifiers that are reloaded from SQL?
3. Which business effects require idempotency and why?
4. How do session, CSRF, membership, RBAC, and tenant filters complement one another?
5. Why are payment and fulfillment modeled independently?
6. How does an approval hash prevent publishing changed content?
7. Why does a serverless web function not replace a persistent worker?
8. Which boundaries can become microservices later, and what evidence would justify that split?
9. What must happen before an integration can be truthfully called live?
10. Which automated tests prove behavior rather than only code structure?
