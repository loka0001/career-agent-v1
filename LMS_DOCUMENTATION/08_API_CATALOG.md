# API Catalog

## Conventions

- Business endpoints are under `/api/v1`.
- Local interactive documentation is `/docs`; exact generated schema is `/openapi.json`.
- Cookie-authenticated state changes require `X-CSRF-Token`.
- Website endpoints use a scoped `X-API-Key` and validate allowed origin where applicable.
- Public abuse controls can also use `X-Client-Fingerprint`.
- Idempotent operations use `Idempotency-Key` or a provider event identifier.
- Webhooks are outside `/api/v1` and authenticate with provider signatures.
- Internal release/job operations require signed release/cron credentials.
- Operator endpoints require an authenticated user in the configured operator allowlist.
- Error responses use the stable `error.code/message/details/request_id` envelope.

The current generated OpenAPI contains 141 paths. The lists below are the complete path catalog;
request/response schemas, validation limits, descriptions, and example payloads should be viewed
in Swagger or `app/api/routes/`.

## Authentication and sessions

| Method | Path                                        | Purpose                                                           |
| ------ | ------------------------------------------- | ----------------------------------------------------------------- |
| POST   | `/api/v1/auth/register`                     | Create account, organization/store, and owner membership          |
| POST   | `/api/v1/auth/verify-email`                 | Consume email-verification token                                  |
| POST   | `/api/v1/auth/resend-verification`          | Issue another verification action                                 |
| POST   | `/api/v1/auth/login`                        | Authenticate, enforce throttling/backoff, issue session/CSRF      |
| POST   | `/api/v1/auth/logout`                       | Revoke current session and clear cookies                          |
| GET    | `/api/v1/auth/me`                           | Current identity, membership, store, entitlements, and CSRF state |
| GET    | `/api/v1/auth/stores`                       | Stores available to the current user                              |
| POST   | `/api/v1/auth/switch-store`                 | Change active membership/store in a new session context           |
| POST   | `/api/v1/auth/forgot-password`              | Issue reset action without account enumeration                    |
| POST   | `/api/v1/auth/reset-password`               | Consume reset token and set a strong password                     |
| POST   | `/api/v1/auth/accept-invite`                | Accept invitation and establish membership                        |
| GET    | `/api/v1/auth/sessions`                     | List revocable sessions                                           |
| POST   | `/api/v1/auth/sessions/{session_id}/revoke` | Revoke one session                                                |
| POST   | `/api/v1/auth/change-password`              | Verify current password and rotate credential/sessions            |
| POST   | `/api/v1/auth/mfa/setup`                    | Begin MFA enrollment                                              |
| POST   | `/api/v1/auth/mfa/confirm`                  | Confirm MFA enrollment/code                                       |
| POST   | `/api/v1/auth/mfa/disable`                  | Disable MFA after reauthentication                                |

## Dashboard, analytics, and customers

| Method | Path                                    | Purpose                                                                  |
| ------ | --------------------------------------- | ------------------------------------------------------------------------ |
| GET    | `/api/v1/dashboard`                     | Tenant-scoped operating snapshot                                         |
| GET    | `/api/v1/analytics`                     | Channel-filterable revenue, conversation, content, agent, and AI metrics |
| GET    | `/api/v1/customers`                     | Customer intelligence list                                               |
| GET    | `/api/v1/customers/{customer_id}`       | Intelligence, score evidence, segments, and timeline                     |
| POST   | `/api/v1/customers/{customer_id}/merge` | Audited merge of two store-scoped identities                             |

## Catalog and inventory

| Method | Path                                                   | Purpose                                            |
| ------ | ------------------------------------------------------ | -------------------------------------------------- |
| GET    | `/api/v1/products`                                     | List store products                                |
| POST   | `/api/v1/products/onboard`                             | Validate image, generate draft, persist, and index |
| GET    | `/api/v1/products/{product_id}`                        | Read one store-scoped product                      |
| PATCH  | `/api/v1/products/{product_id}`                        | Review/update permitted authoritative fields       |
| POST   | `/api/v1/products/{product_id}/activate`               | Apply product lifecycle activation                 |
| GET    | `/api/v1/products/{product_id}/variants`               | List variants                                      |
| POST   | `/api/v1/products/{product_id}/variants`               | Add a validated variant                            |
| POST   | `/api/v1/products/{product_id}/inventory/adjust`       | Append idempotent inventory adjustment             |
| GET    | `/api/v1/products/{product_id}/inventory/transactions` | Read inventory ledger                              |
| POST   | `/api/v1/products/{product_id}/marketing-packs`        | Generate pack from reviewed facts                  |

## Marketing, Content Studio, and publications

| Method | Path                                          | Purpose                                 |
| ------ | --------------------------------------------- | --------------------------------------- |
| GET    | `/api/v1/marketing-packs/{pack_id}`           | Read generated marketing content        |
| PATCH  | `/api/v1/marketing-packs/{pack_id}`           | Edit, version, and revalidate content   |
| POST   | `/api/v1/marketing-packs/{pack_id}/approve`   | Store actor/version/hash approval       |
| POST   | `/api/v1/marketing-packs/{pack_id}/publish`   | Idempotently publish selected platforms |
| GET    | `/api/v1/publications/{publication_id}`       | Read saved provider publication attempt |
| GET    | `/api/v1/studio/brand`                        | Read brand profile                      |
| PUT    | `/api/v1/studio/brand`                        | Update brand profile                    |
| GET    | `/api/v1/studio/content`                      | List content/calendar items             |
| POST   | `/api/v1/studio/content/generate`             | Generate validated content item         |
| PATCH  | `/api/v1/studio/content/{item_id}`            | Edit and create content version         |
| POST   | `/api/v1/studio/content/{item_id}/regenerate` | Regenerate a selected section           |
| GET    | `/api/v1/studio/content/{item_id}/versions`   | Read version history                    |
| POST   | `/api/v1/studio/content/{item_id}/approve`    | Approve current content version         |
| POST   | `/api/v1/studio/content/{item_id}/publish`    | Queue approved publication              |
| POST   | `/api/v1/studio/campaigns/generate`           | Generate multi-item campaign            |

## Inbox and sales assistant

| Method | Path                                                    | Purpose                                                           |
| ------ | ------------------------------------------------------- | ----------------------------------------------------------------- |
| GET    | `/api/v1/inbox/conversations`                           | Filtered/paginated conversation summaries                         |
| GET    | `/api/v1/inbox/conversations/{conversation_id}`         | Conversation detail and messages                                  |
| PATCH  | `/api/v1/inbox/conversations/{conversation_id}`         | Assignment, status, priority, or read state                       |
| POST   | `/api/v1/inbox/conversations/{conversation_id}/reply`   | Queue consent-aware outbound reply                                |
| POST   | `/api/v1/inbox/conversations/{conversation_id}/suggest` | Produce grounded reply suggestion                                 |
| POST   | `/api/v1/inbox/conversations/{conversation_id}/notes`   | Add internal note                                                 |
| POST   | `/api/v1/inbox/simulate`                                | Explicit local/demo inbound simulation                            |
| POST   | `/api/v1/inbox/mark-all-read`                           | Mark current store conversations read                             |
| POST   | `/api/v1/sales/assist`                                  | Extract need, retrieve/rank, generate and validate grounded reply |

## Orders and demo collection

| Method | Path                                   | Purpose                                                 |
| ------ | -------------------------------------- | ------------------------------------------------------- |
| GET    | `/api/v1/orders`                       | List store orders                                       |
| POST   | `/api/v1/orders`                       | Create server-calculated draft order                    |
| GET    | `/api/v1/orders/{order_id}`            | Items, totals, addresses, payment/fulfillment, timeline |
| POST   | `/api/v1/orders/{order_id}/transition` | Apply legal state transition and optional notification  |
| POST   | `/api/v1/orders/{order_id}/checkout`   | Prepare configured COD/payment flow                     |
| GET    | `/checkout/demo/{order_id}`            | Show signed, isolated no-money demo checkout            |
| POST   | `/checkout/demo/{order_id}`            | Confirm explicitly labelled demo collection             |

## Opportunities and automations

| Method | Path                                              | Purpose                                        |
| ------ | ------------------------------------------------- | ---------------------------------------------- |
| GET    | `/api/v1/opportunities`                           | List explainable prioritized opportunities     |
| GET    | `/api/v1/opportunities/dashboard`                 | Value/lifecycle/conversion funnel              |
| POST   | `/api/v1/opportunities/scan`                      | Enqueue deduplicated detector run              |
| POST   | `/api/v1/opportunities/{opportunity_id}/decision` | Approve, execute, reject, or attribute outcome |
| GET    | `/api/v1/automations`                             | List definitions                               |
| POST   | `/api/v1/automations`                             | Create definition                              |
| GET    | `/api/v1/automations/runs`                        | Run/retry/approval history                     |
| GET    | `/api/v1/automations/templates`                   | Installable templates                          |
| POST   | `/api/v1/automations/templates/{template_key}`    | Install selected template                      |
| POST   | `/api/v1/automations/events`                      | Ingest deduplicated business trigger           |
| POST   | `/api/v1/automations/runs/{run_id}/approve`       | Resume approval-gated action                   |
| POST   | `/api/v1/automations/{automation_id}/enable`      | Enable definition                              |
| POST   | `/api/v1/automations/{automation_id}/disable`     | Disable definition                             |

## Integration overview and generic connections

| Method | Path                                                          | Purpose                                     |
| ------ | ------------------------------------------------------------- | ------------------------------------------- |
| GET    | `/api/v1/integrations`                                        | Aggregate secret-safe provider readiness    |
| POST   | `/api/v1/integrations/meta/check`                             | Read-only current-store Meta check          |
| GET    | `/api/v1/integrations/connections`                            | List encrypted provider connection metadata |
| POST   | `/api/v1/integrations/connections/{connection_id}/check`      | Refresh health/capabilities                 |
| POST   | `/api/v1/integrations/connections/{connection_id}/disconnect` | Disable/revoke local connection state       |

## Commerce connections

| Method | Path                                                   | Purpose                                                  |
| ------ | ------------------------------------------------------ | -------------------------------------------------------- |
| POST   | `/api/v1/integrations/commerce`                        | Create validated encrypted commerce connection           |
| POST   | `/api/v1/integrations/commerce/shopify/oauth/start`    | Start signed merchant Shopify install                    |
| POST   | `/api/v1/integrations/commerce/shopify/oauth/exchange` | Verify/exchange callback and save encrypted token        |
| POST   | `/api/v1/integrations/commerce/{connection_id}/sync`   | Enqueue or run idempotent catalog/order sync             |
| GET    | `/shopify/oauth/callback`                              | Validate browser callback and redirect to integration UI |
| POST   | `/webhooks/commerce/{connection_id}`                   | Signed commerce webhook ingestion                        |

## Meta and WhatsApp channels

| Method | Path                                                                     | Purpose                                      |
| ------ | ------------------------------------------------------------------------ | -------------------------------------------- |
| GET    | `/api/v1/integrations/meta/channels`                                     | List masked channel state                    |
| PUT    | `/api/v1/integrations/meta/channels/{channel_type}`                      | Save encrypted manual channel settings       |
| POST   | `/api/v1/integrations/meta/channels/{channel_id}/check`                  | Check permissions/token/account health       |
| POST   | `/api/v1/integrations/meta/channels/oauth/start`                         | Create signed OAuth state                    |
| POST   | `/api/v1/integrations/meta/channels/oauth/exchange`                      | Exchange callback code and discover accounts |
| POST   | `/api/v1/integrations/meta/channels/oauth/connect`                       | Connect selected Page/Instagram assets       |
| GET    | `/meta/oauth/callback`                                                   | Validate callback and redirect to UI         |
| GET    | `/webhooks/meta/{channel_id}`                                            | Meta verification challenge                  |
| POST   | `/webhooks/meta/{channel_id}`                                            | Signed DM/comment event ingestion            |
| GET    | `/api/v1/integrations/whatsapp`                                          | Read masked per-store WhatsApp status        |
| PUT    | `/api/v1/integrations/whatsapp`                                          | Save encrypted manual WhatsApp settings      |
| POST   | `/api/v1/integrations/whatsapp/embedded/start`                           | Start embedded signup                        |
| POST   | `/api/v1/integrations/whatsapp/embedded/exchange`                        | Exchange embedded signup result              |
| POST   | `/api/v1/integrations/whatsapp/embedded/connect`                         | Connect selected phone/account               |
| POST   | `/api/v1/integrations/whatsapp/check`                                    | Read-only Cloud API health check             |
| GET    | `/api/v1/integrations/whatsapp/templates`                                | List reconciled templates                    |
| POST   | `/api/v1/integrations/whatsapp/templates`                                | Register template metadata                   |
| POST   | `/api/v1/integrations/whatsapp/templates/sync`                           | Sync provider templates                      |
| POST   | `/api/v1/integrations/whatsapp/conversations/{conversation_id}/template` | Queue approved template send                 |
| POST   | `/api/v1/integrations/whatsapp/conversations/{conversation_id}/media`    | Queue validated media send                   |
| GET    | `/webhooks/whatsapp/{channel_id}`                                        | WhatsApp verification challenge              |
| POST   | `/webhooks/whatsapp/{channel_id}`                                        | Signed message/status webhook ingestion      |

## Website/public integration

| Method | Path                                   | Purpose                                         |
| ------ | -------------------------------------- | ----------------------------------------------- |
| GET    | `/api/v1/public/catalog`               | Active store catalog for scoped publishable key |
| POST   | `/api/v1/public/chat`                  | Consent-aware website assistant/inbox ingestion |
| POST   | `/api/v1/public/events`                | Batched website consent/behavior events         |
| GET    | `/widget.js`                           | Embeddable website widget runtime               |
| GET    | `/media/{asset_id}`                    | Controlled database-backed media delivery       |
| GET    | `/private-media/{store_id}/{filename}` | Signed tenant-bound local private media         |

## Billing and payment webhooks

| Method | Path                           | Purpose                                          |
| ------ | ------------------------------ | ------------------------------------------------ |
| GET    | `/api/v1/billing/plans`        | Server plan definitions and limits               |
| GET    | `/api/v1/billing/subscription` | Current entitlement/usage/subscription state     |
| POST   | `/api/v1/billing/subscription` | Start/change plan when commercial mode allows    |
| GET    | `/api/v1/billing/capabilities` | Truthful billing feature/provider availability   |
| POST   | `/api/v1/billing/portal`       | Create provider billing-portal link when enabled |
| POST   | `/webhooks/stripe/billing`     | Signed subscription/billing events               |
| POST   | `/webhooks/stripe/payments`    | Signed merchant order payment events             |

## Team, settings, and API keys

| Method | Path                                   | Purpose                                             |
| ------ | -------------------------------------- | --------------------------------------------------- |
| GET    | `/api/v1/team`                         | List memberships                                    |
| POST   | `/api/v1/team`                         | Invite member and return one-time credential/action |
| PATCH  | `/api/v1/team/{membership_id}`         | Change role with owner safeguards                   |
| POST   | `/api/v1/team/{membership_id}/revoke`  | Revoke membership                                   |
| GET    | `/api/v1/settings/store`               | Read store/assistant settings                       |
| PUT    | `/api/v1/settings/store`               | Save validated settings                             |
| GET    | `/api/v1/settings/onboarding`          | Read activation checklist                           |
| POST   | `/api/v1/settings/onboarding/activate` | Activate completed store onboarding                 |
| GET    | `/api/v1/api-keys`                     | List masked website keys                            |
| POST   | `/api/v1/api-keys`                     | Create scoped key; secret returned once             |
| POST   | `/api/v1/api-keys/{key_id}/revoke`     | Revoke key                                          |

## Privacy and legal

| Method | Path                                             | Purpose                                |
| ------ | ------------------------------------------------ | -------------------------------------- |
| GET    | `/api/v1/privacy/export`                         | Export current store/account data      |
| GET    | `/api/v1/privacy/customers/{customer_id}/export` | Export one customer within tenant      |
| GET    | `/api/v1/privacy/retention`                      | Read retention policy                  |
| PUT    | `/api/v1/privacy/retention`                      | Save retention policy                  |
| POST   | `/api/v1/privacy/account-deletion`               | Authenticated account deletion request |
| POST   | `/api/v1/privacy/store-deletion`                 | Owner store deletion request           |
| GET    | `/api/v1/privacy/deletions/{request_id}`         | Read authorized deletion state         |
| GET    | `/api/v1/privacy/public-deletions/{request_id}`  | Safe public deletion status            |
| GET    | `/api/v1/privacy/media/{asset_id}/url`           | Generate authorized expiring media URL |
| POST   | `/webhooks/meta/data-deletion`                   | Meta signed data-deletion request      |
| GET    | `/api/v1/legal/privacy`                          | Privacy content contract               |
| GET    | `/api/v1/legal/terms`                            | Terms content contract                 |

## Operator and internal operations

| Method | Path                                             | Purpose                                            |
| ------ | ------------------------------------------------ | -------------------------------------------------- |
| GET    | `/api/v1/operator/overview`                      | Cross-store system overview                        |
| GET    | `/api/v1/operator/alerts`                        | Computed readiness/queue/provider alerts           |
| GET    | `/api/v1/operator/jobs`                          | Inspect durable jobs                               |
| POST   | `/api/v1/operator/jobs/{job_id}/replay`          | Audited replay of eligible failed job              |
| GET    | `/api/v1/operator/audit`                         | Search audit evidence                              |
| GET    | `/api/v1/operator/stores`                        | Search store operational state                     |
| PATCH  | `/api/v1/operator/stores/{store_id}/suspension`  | Suspend/resume with reason                         |
| GET    | `/api/v1/operator/stores/{store_id}/diagnostics` | Tenant diagnostics without secret disclosure       |
| GET    | `/api/v1/operator/webhooks`                      | Provider webhook health/dedup state                |
| GET    | `/api/v1/internal/jobs/drain`                    | Signed recovery drain contract                     |
| POST   | `/api/v1/internal/jobs/recover-stale`            | Requeue expired leases without arbitrary execution |
| GET    | `/api/v1/internal/jobs/diagnostics`              | Read worker diagnostic marker/state                |
| POST   | `/api/v1/internal/jobs/diagnostics`              | Create signed worker diagnostic work               |
| POST   | `/api/v1/internal/release/migrate`               | Explicit authorized release migration operation    |
| POST   | `/api/v1/internal/release/verify-migrations`     | Verify expected migration head                     |

## Health

| Method | Path            | Purpose                                     |
| ------ | --------------- | ------------------------------------------- |
| GET    | `/health/live`  | Process liveness                            |
| GET    | `/health/ready` | Database/search/queue and runtime readiness |
