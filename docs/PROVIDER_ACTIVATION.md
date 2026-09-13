# Provider Activation

Last reviewed: 2026-08-01

Do not mark a provider active until a production request succeeds through the application or the
provider blocks testing pending owner/legal approval.

## OpenAI

Status: completed but awaiting external activation.

Required owner action: provide an approved production OpenAI or Vercel AI Gateway credential,
model policy, budget ceiling, and allowed data-use policy. Store the key in Vercel, set
`AI_PROVIDER=openai`, and verify with an authenticated application generation request.

## Transactional Email

Status: completed but awaiting external activation.

Required owner action: choose and verify the sender domain for Resend, add DNS records, set
`EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and `EMAIL_FROM`, then send one authorized password-reset
test to the owner.

Technical prerequisite status: application startup now rejects `EMAIL_PROVIDER=resend` unless
`EMAIL_FROM` is exactly one safe sender email address with a real domain shape and no header
injection characters.

## Meta And WhatsApp

Status: completed but awaiting external activation.

Required owner action: complete Meta Business verification, WhatsApp phone verification, Embedded
Signup setup, app review, and template approval. Configure callback URLs to the production domain
and store per-merchant credentials through the app, not global source files.

Technical prerequisite status: signed WhatsApp webhooks verify `X-Hub-Signature-256`, deduplicate
events, and ignore inbound/status events whose `metadata.phone_number_id` does not match the
configured channel phone-number ID. This is local technical readiness only; it is not proof of Meta
business verification, phone ownership, template approval, or authorized message delivery.

## Meta Social Publishing And Inbox

Status: completed locally but awaiting external activation.

Required owner action: complete Meta app setup/review for Facebook Page and Instagram Business
capabilities, set `ENABLE_REAL_PUBLISHING=true` only after approval, configure the production
`META_OAUTH_REDIRECT_URI`, and connect merchant Facebook/Instagram assets through the application
OAuth flow so credentials are stored per store in the encrypted provider vault.

Technical prerequisite status: local code covers OAuth account selection, encrypted per-store
provider connections, signed DM/comment webhooks, permission and token-expiry reporting, bounded
Instagram publishing polling, provider-aware publishing, and tenant-isolation tests. This is not
proof of live Facebook/Instagram publishing or inbox delivery until an authorized publish and
signed inbound event succeed against merchant assets.

The operator Meta check endpoint follows the same per-store model: when a store has Meta OAuth
connections, `/api/v1/integrations/meta/check` checks those encrypted current-store connections
and returns secret-safe aggregate status instead of requiring forbidden global merchant publisher
credentials.

## Commerce Connectors

Status: completed locally but awaiting merchant store activation.

Required owner action: connect an authorized Shopify, WooCommerce, or generic commerce store
through the application, confirm the production callback URL from `PUBLIC_BASE_URL`, and keep
store OAuth tokens, access tokens, consumer secrets, and webhook secrets in the encrypted app
connection flow, not in committed files. For Shopify OAuth, configure `SHOPIFY_APP_API_KEY`,
`SHOPIFY_APP_API_SECRET`, `SHOPIFY_OAUTH_REDIRECT_URI`, and `SHOPIFY_OAUTH_SCOPES` in the runtime
environment before starting installation.

Technical prerequisite status: local API coverage verifies connector creation, credential
redaction, idempotent catalog/order sync, signed webhook acceptance/rejection, duplicate webhook
safety, sync job enqueueing, and cross-tenant access denial. Shopify direct custom-app token
connection works. Shopify OAuth installation is now implemented locally with an authenticated
browser callback redirect, integrations UI start/exchange wiring, signed HMAC callback validation,
invalid-signature rejection before state consumption, server-side token exchange, encrypted
provider-connection creation, Shopify app-secret HMAC verification for OAuth-installed store
webhooks, OAuth transaction cleanup, and optional webhook registration. This is still not live
Shopify activation until a merchant shop authorizes the app and a credentialed sync/webhook smoke
succeeds.

## Media Storage

Status: completed and production-verified for database-backed media.

Production setting: `IMAGE_STORAGE_PROVIDER=database`. Cloudinary remains a supported external
option but is not activated without account credentials and malware-scanning policy acceptance.

Technical prerequisite status: operator-facing integration status now treats database-backed media
as configured, local media as not production-configured, Cloudinary as configured only with the full
credential set, and malware-scanner readiness as visible/fail-closed in production.

## Stripe

Status: completed but awaiting external activation.

COD must remain available while Stripe is disabled. Required owner action: complete Stripe merchant
onboarding, configure live/test keys and webhook secrets, create prices, and authorize a low-risk
production verification transaction. Do not enable `BILLING_PROVIDER=stripe` or
`PAYMENT_PROVIDER=stripe` until checkout, webhook, duplicate event, refund/cancel, and inventory
consistency tests pass.

## Monitoring

Status: partially completed.

Vercel runtime logs and health checks are available. Sentry is supported through `SENTRY_DSN`, but
no production DSN is currently present in the Vercel environment-variable listing.

Production startup readiness warnings now include missing `SENTRY_DSN`, `OPERATOR_EMAILS`, and
`RELEASE_SHA`, so a production process can surface missing alert delivery, operator access, and
release attribution without logging secret values.

## Evidence Gate

Run `python scripts/verify_provider_status.py` before release handoff. The verifier checks
`artifacts/agent/provider-status.json` for the approved status vocabulary, required provider
records, required fields, timestamp syntax, environment-key names without values, and
secret-looking strings. It does not prove external activation; live provider status still requires
the credentialed acceptance tests listed above.

Run `python scripts/verify_environment_matrix.py` after provider or environment-name changes. It
checks `artifacts/production-readiness/environment-matrix.md` against the provider-required key
names and rejects secret-looking values or accidental `KEY=value` entries.

Run `python scripts/verify_env_example.py` after adding or renaming provider environment keys. It
keeps `.env.example` aligned with provider-status and critical runtime names while requiring
sensitive template values to stay blank.
