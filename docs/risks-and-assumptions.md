# Risks and Assumptions

Last audited: 2026-07-30

| Risk/assumption | Impact | Current control | Next validation |
| --- | --- | --- | --- |
| Meta API versions, permissions, and reviews change. | Messaging or publishing can stop. | Versioned adapters, explicit capability status, signed webhooks, fail-closed provider errors. | Quarterly official-document review and credentialed staging smoke. |
| Merchant media URLs or storage are not provider-reachable. | Real publishing can fail. | HTTPS checks, private media model, replaceable object-storage adapter. | Verify one controlled merchant asset and retention policy. |
| AI can invent facts or follow hostile customer text. | Trust, compliance, and margin damage. | Structured output, catalog/policy allowlists, prompt-injection boundary, factual validation, approval, budget and circuit breaker. | Run the credentialed evaluation dataset before model changes. |
| Provider credentials are unavailable or expired. | External actions cannot complete. | Per-store encrypted secrets, masked diagnostics, expiry/permission state, actionable setup UI; no fake success. | Credentialed account-selection, send, publish, disconnect, and expiry test. |
| Daily recovery cron is not a timely scheduler. | Scheduled posts and automation delays can be late. | Durable jobs, leases, retries, signed recovery drain, standalone worker contract. | Deploy and alert on an independent worker runtime. |
| Free access is mistaken for unlimited or Demo access. | Cost or policy drift. | Server Growth entitlement, retained quotas/features/RBAC/audit, no provider billing IDs, explicit Demo badge only when Demo is enabled. | Review usage and cost limits before changing the access flag. |
| Production registration has no email provider. | New users cannot verify accounts. | Fail-closed registration; no verification bypass. | Activate a verified sending domain and test delivery, bounce, resend, recovery. |
| Legal, retention, and subprocessors text is not approved. | General availability compliance risk. | Privacy/export/deletion mechanisms exist; activation checklist requires approval. | Named legal owner signs off before public acquisition. |
| Seed and Demo data are not market evidence. | Misleading commercial claims. | Landing page contains no fabricated metrics; Demo is globally labelled as isolated. | Pilot with real merchants and report only measured outcomes. |
| Docker is unavailable on the current workstation. | Local image/Trivy proof is absent. | Docker and scanning are configured in CI; source/runtime gates run independently. | Execute the container gate on CI or a Docker-capable runner. |
| No Git metadata is present in this workspace snapshot. | A commit diff and rollback SHA cannot be produced locally. | File-level inventories and verification artifacts record the candidate state. | Import into the canonical repository and create a reviewed release commit. |

## External tests not executed by default

Live OpenAI, object storage, Meta/Facebook/Instagram, WhatsApp, Stripe, and email behavior
cannot be claimed without merchant-owned credentials, provider/account state, public
HTTPS callbacks, and explicit activation. Real adapters and contract tests exist;
deterministic/fake paths are restricted to explicit Demo mode.
