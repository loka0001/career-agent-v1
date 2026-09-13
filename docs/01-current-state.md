# Current State

Last reconciled: 2026-09-06

## Delivered runtime

The current modular monolith includes FastAPI, the React/Vite merchant application, SQLAlchemy and
Alembic persistence, a durable independent worker, first-party authentication, catalog/inventory,
orders, opportunities, automations, analytics, a unified inbox, content approval/publishing,
privacy operations, and production-shaped provider boundaries. See
`docs/REPOSITORY_TRUTH_AUDIT.md` for the authoritative code/test/demo/live matrix.

## Current verification boundary

The SQLite deterministic demo and its two primary browser journeys pass locally. Disposable
PostgreSQL 17.10 clean/upgrade migrations and a representative logical dump/restore also pass.
Price, stock, catalog identity, policy evidence, tenant scope, approvals, and idempotency remain
server-owned.
The AI evaluation layer includes 15 normal Arabic/English questions and eight adversarial commerce
vectors, plus injected hostile model-output tests that prove validation retry and deterministic
fallback.
The broad browser matrix now also proves useful loading, empty, network-unavailable,
provider-disconnected, AI-unavailable, publish-failed, Home partial-source failure,
permission-denied, and expired-session states. Home prioritizes real conversation replies,
content decisions, publishing attention, and channel setup from typed APIs; publication status
guidance and the integrations workflow are localized in Arabic and English, including the compact
mobile layout.
The desktop shell now exposes only the six P0 merchant jobs as primary navigation. Secondary
working modules remain reachable through an accessible disclosure and command palette, while the
mobile bar prioritizes Home, Inbox, Content, Products, and More.

This does not establish production readiness. The current candidate has no Git remote or immutable
release SHA evidence, managed PostgreSQL migration/restore result, current deployment access,
persistent production-worker evidence, credentialed live-provider acceptance, or merchant sign-off.

## Architecture principles retained

- Strict Pydantic boundary contracts and versioned structured-output prompts.
- Replaceable, fail-closed integration interfaces.
- Local deterministic adapters for development and CI, never represented as live proof.
- Store-scoped repositories as the authority for mutable commerce facts.
- Explicit human approval evidence before external content publication.
