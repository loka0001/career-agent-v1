# Capability Matrix

Last audited: 2026-07-30

`Ready` means the tenant-scoped database, API, policy, UI where applicable, and
automated contract exist. `Provider activation` means the real adapter exists but no
merchant-owned credentialed acceptance test was available.

| Capability | State | Verification and limitation |
| --- | --- | --- |
| Website assistant and catalog | Ready | Origin-bound API keys, consent events, inbox capture, catalog scope, and database-backed rate limits are tested. |
| Unified Inbox | Ready | Website, WhatsApp, Messenger, Instagram DM, and Facebook/Instagram comments are modelled and tenant-tested. |
| WhatsApp receive/send/status | Provider activation | Signed webhooks, service window, templates, consent, retries, and per-store secrets are tested with fakes. |
| Meta DM/comment channels | Provider activation | OAuth/manual setup, signatures, permissions, expiry, account selection, and masked status exist. |
| Grounded recommendations | Provider activation | Factual constraints and deterministic Demo provider are tested; production fails closed without an AI credential. |
| Catalog and inventory | Ready | Variants, source-of-truth, stock policy, row-locked ledger, reservation/release, and reconciliation are tested. |
| Orders and COD | Ready | Multi-line creation, server totals, idempotency, lifecycle, separate payment/fulfillment state, COD, and cancellation are tested and browser-verified. |
| Stripe billing/card collection | Dormant | Provider interfaces, signed webhooks, and state machines remain; launch UI/API do not create checkout while free access is active. |
| Free SaaS access and quotas | Ready | Active Growth access has no trial/provider IDs; plan/portal mutations reject; quotas, features, RBAC, audit, and tenant isolation remain enforced. |
| Customer intelligence | Ready | Identity merge, RFM evidence, consent, segments, preferences, and tenant isolation are tested. |
| Revenue opportunities | Ready | Explainable detector families, approval, execution, funnel, and attribution are tested. |
| Automations | Ready | Persisted triggers, conditions, delay, approval, retry, history, leases, and durable worker actions are tested. |
| Social content generation | Provider activation | Formats, versions, approval, scheduling, campaigns, factual validation, and provider-aware errors are tested. |
| Facebook/Instagram publishing | Provider activation | Idempotency and isolated fake publishing are tested; real tokens, media hosting, and App Review remain external. |
| Analytics | Ready | Store-scoped SQL metrics for channels, funnels, revenue, content, agents, automations, and AI use a stated 30-day UI context. |
| Team and RBAC | Ready | Five roles, tenant membership, role matrix, invitation security, revocation, and last-owner safeguards are tested. |
| Privacy and media | Ready | Export, retention, deletion jobs, token/session revocation, private tenant-bound media URLs, and scanning hook exist. |
| Multi-tenancy | Ready | Membership and store scope are checked per request; cross-tenant coverage includes free-access and order paths. |
| Deployment scale | Ready with external worker | PostgreSQL, database rate limits, durable SQL jobs, leases, retries, recovery cron, and standalone worker exist; timely scheduling needs the external worker runtime. |

External activation steps live in `PRODUCTION_ACTIVATION.md`. Demo/fake adapters are
available only under explicit `DEMO_MODE=true` and are visibly labelled as isolated
data.
