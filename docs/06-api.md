# API Guide

Interactive OpenAPI is available at `/docs`; all business endpoints use `/api/v1`.

## Endpoints

| Method | Path | Auth/CSRF | Result |
| --- | --- | --- | --- |
| POST | `/auth/login` | No | Session and CSRF cookies. |
| POST | `/auth/logout` | Session + CSRF | Clears cookies. |
| GET | `/auth/me` | Session | Merchant and CSRF token. |
| GET | `/products` | Session | Catalog list. |
| POST | `/products/onboard` | Session + CSRF | Multipart draft product. |
| GET | `/products/{id}` | Session | One product. |
| PATCH | `/products/{id}` | Session + CSRF | Reviewed product. |
| POST | `/products/{id}/activate` | Session + CSRF | Active product. |
| POST | `/products/{id}/marketing-packs` | Session + CSRF | Draft platform content. |
| GET/PATCH | `/marketing-packs/{id}` | Session; CSRF on PATCH | Read/edit content. |
| POST | `/marketing-packs/{id}/approve` | Session + CSRF | Stored approval hash/version. |
| POST | `/marketing-packs/{id}/publish` | Session + CSRF + idempotency | Per-platform results. |
| GET | `/publications/{id}` | Session | Saved publication attempt. |
| GET | `/integrations` | Session | Secret-safe status. |
| POST | `/integrations/meta/check` | Session + CSRF | Read-only connection test. |
| GET/PUT | `/integrations/whatsapp` | Admin; CSRF on PUT | Masked status and encrypted per-store settings. |
| POST | `/integrations/whatsapp/check` | Admin + CSRF | Read-only Cloud API connection check; never sends. |
| GET/POST | `/integrations/whatsapp/templates` | Admin; CSRF on POST | List or register WhatsApp templates. |
| POST | `/integrations/whatsapp/conversations/{id}/template` | Admin + CSRF | Queue an approved template with validated variables. |
| GET/POST | `/webhooks/whatsapp/{channel_id}` | Public signed webhook | Meta verification challenge or signed event receipt. |
| GET/POST | `/orders` | Session; Agent + CSRF on POST | List orders or create a validated draft from a conversation. |
| GET | `/orders/{id}` | Session | Order items, totals, shipping data, and status timeline. |
| POST | `/orders/{id}/transition` | Agent + CSRF | Apply a legal domain status transition. |
| POST | `/orders/{id}/checkout` | Agent + CSRF | Prepare the configured collection flow; COD records collection confirmation without a card link. |
| GET/POST | `/checkout/demo/{id}` | Signed public token; Demo only | Display or confirm the explicitly labelled isolated no-money Demo checkout. |
| GET | `/customers`, `/customers/{id}` | Session | Explainable score, segments, revenue, AOV, and preferences. |
| POST | `/customers/{id}/merge` | Admin + CSRF | Merge two store-scoped customer identities with an audit trail. |
| GET | `/opportunities` | Session | Prioritized revenue opportunities from deterministic rules. |
| GET | `/opportunities/dashboard` | Session | Opportunity value, lifecycle, and conversion funnel. |
| POST | `/opportunities/scan` | Agent + CSRF | Queue an idempotent detector scan. |
| POST | `/opportunities/{id}/decision` | Agent + CSRF | Approve, execute, reject, or attribute won revenue. |
| GET/POST | `/automations` | Session; Marketer + CSRF on POST | List or create persisted automation definitions. |
| GET | `/automations/runs`, `/automations/templates` | Session | Run history and installable templates. |
| POST | `/automations/events` | Agent + CSRF | Ingest a deduplicated business trigger. |
| POST | `/automations/runs/{id}/approve` | Marketer + CSRF | Approve a paused automation action. |
| POST | `/automations/{id}/{enable,disable}` | Marketer + CSRF | Control automation execution. |
| GET/PUT | `/studio/brand` | Session; Marketer + CSRF on PUT | Read or update the store brand profile. |
| GET/POST | `/studio/content` | Session; Marketer + CSRF on POST | Content calendar items and validated generation. |
| PATCH | `/studio/content/{id}` | Marketer + CSRF | Edit content and create a version. |
| POST | `/studio/content/{id}/regenerate` | Marketer + CSRF | Regenerate one selected section. |
| GET | `/studio/content/{id}/versions` | Session | Version history. |
| POST | `/studio/content/{id}/{approve,publish}` | Marketer + CSRF | Approve or queue publication. |
| POST | `/studio/campaigns/generate` | Marketer + CSRF | Generate a multi-post campaign from catalog facts. |
| GET | `/analytics` | Session | Channel-filtered conversation, revenue, content, agent, and AI metrics. |
| GET/POST | `/billing/subscription` | Session; Owner + CSRF on POST | Read access/usage; plan changes return `409` while free access is active. |
| GET | `/billing/plans` | Session | Plan limits for server quota enforcement; no launch pricing/checkout is shown in free mode. |
| GET/PUT | `/settings/store` | Session; Admin + CSRF on PUT | Store, assistant, and onboarding settings. |
| GET/POST | `/team` | Admin; Owner + CSRF on POST | List members or issue a one-time temporary credential. |
| PATCH/POST | `/team/{id}`, `/team/{id}/revoke` | Owner + CSRF | Change role or revoke access with owner safeguards. |
| GET/POST | `/api-keys` | Admin + CSRF on POST | Website integration keys; secret returned once. |
| POST | `/api-keys/{id}/revoke` | Admin + CSRF | Revoke a website key. |
| GET/PUT | `/integrations/meta/channels/{type}` | Admin; CSRF on PUT | Masked Meta channel setup. |
| POST | `/integrations/meta/channels/oauth/start` | Admin + CSRF | Begin OAuth onboarding. |
| POST | `/integrations/meta/channels/oauth/exchange` | Admin + CSRF | Exchange the callback code and discover accounts. |
| POST | `/integrations/meta/channels/oauth/connect` | Admin + CSRF | Connect selected Page and Instagram accounts. |
| POST | `/integrations/commerce/shopify/oauth/start` | Admin + CSRF | Begin signed Shopify OAuth installation for a merchant shop. |
| POST | `/integrations/commerce/shopify/oauth/exchange` | Admin + CSRF | Verify Shopify callback HMAC, exchange code server-side, and create an encrypted store connection. |
| GET | `/shopify/oauth/callback` | Authenticated browser callback | Validate signed Shopify callback state/HMAC and redirect to the integrations UI for single-use exchange. |
| GET/POST | `/webhooks/meta/{channel_id}` | Public signed webhook | Verification or signed DM/comment ingestion. |
| POST | `/public/chat`, `/public/events` | API key | Website assistant and consent-aware event ingestion. |
| GET | `/public/catalog` | API key | Active, store-scoped product catalog. |
| GET | `/dashboard` | Session | Aggregated store overview: product/content/publishing/sales stats, low-stock list, recent activity. |
| POST | `/sales/assist` | Session + CSRF | Need, up to three products, reply, citations. |
| GET | `/health/live`, `/health/ready` | Public | Process and DB/vector readiness. |
| POST | `/internal/jobs/recover-stale` | Release Bearer credential | Requeue abandoned leased jobs without executing pending customer/provider work. |

## Manual API test

Login and save cookies:

```bash
curl -i -c cookies.txt http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"merchant@example.com","password":"YOUR_LOCAL_PASSWORD"}'
```

Copy `csrf_token` from the JSON response, then ask the public sales endpoint:

```bash
curl http://localhost:8000/api/v1/sales/assist \
  -H 'Content-Type: application/json' \
  -d '{"message":"عايز سماعة للمكالمات وميزانيتي 1500 جنيه"}'
```

List products using the cookie:

```bash
curl -b cookies.txt http://localhost:8000/api/v1/products
```

State-changing authenticated calls also require `-H 'X-CSRF-Token: COPIED_TOKEN'`. Publishing additionally requires a unique `Idempotency-Key` header. Public website endpoints use `X-API-Key`.

## Error contract

```json
{
  "error": {
    "code": "content_not_approved",
    "message": "المحتوى يحتاج إلى موافقة قبل النشر.",
    "details": {},
    "request_id": "e7f..."
  }
}
```

The API also returns `402` with error code `quota_exceeded` when the organization exceeds a server-enforced plan limit. Validation, authorization, conflict, and provider failures retain the same envelope with an appropriate status code and request ID.

Expected codes: 400 invalid input, 401 missing/invalid session, 403 CSRF/authorization, 404 missing entity, 409 invalid lifecycle state, 422 schema failure, 502 external provider failure, and 503 missing/unavailable integration.

## WhatsApp webhook contract

Configure Meta to use `/webhooks/whatsapp/{channel_id}`. The GET challenge uses the
per-channel verify token. Every POST must include `X-Hub-Signature-256`; the application
verifies HMAC-SHA256 against the encrypted App Secret before parsing or storing the payload.
Webhook retries are idempotent by WhatsApp message ID.

Free-form WhatsApp replies are rejected once 24 hours have elapsed since the latest inbound
message. An approved template is required after that point. All outbound paths also require
explicit WhatsApp consent.
