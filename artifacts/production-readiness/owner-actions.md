# Owner Actions

Generated: 2026-08-01

This file lists owner-controlled actions that cannot be completed safely from this local
workspace. It records field names and value sources only; do not place secret values here.

## Current Sequential Blocker

| Field | Value |
| --- | --- |
| Provider | GitHub / canonical Git repository |
| Exact page | Canonical repository `Code` page, then repository `Settings` → `Branches` and `Actions` |
| Exact account or project | The production source repository for `G:\Latest-Ai-Project\commerce-ai-mvp` |
| Exact field | Repository remote URL, protected continuation branch, required checks, and Actions secrets/environment names |
| Value source | Existing local workspace plus the owner-controlled canonical repository |
| Reason | The local workspace has no `.git`, so branch, commit, PR, and CI evidence cannot be produced. |
| Expected result | All local changes are imported into the canonical repository on a dedicated continuation branch with CI enabled. |
| Verification step after completion | Import files whose hashes are listed in `artifacts/production-readiness/repository-handoff-manifest.json`, run `git status --short --branch`, `git remote -v`, `uv run python scripts/verify_repository_handoff_manifest.py`, and `uv run python scripts/verify_git_integrity.py --require-release-sha`; then open a PR and confirm GitHub Actions pass. |

## Next Action After Git Is Restored

| Field | Value |
| --- | --- |
| Provider | Vercel |
| Exact page | Vercel Dashboard → Team `malek-virtz` → Project `commerce-revenue-autopilot` → Deployments and Settings → Environment Variables |
| Exact account or project | `commerce-revenue-autopilot` / `prj_qd8XsbNvKkxWQvDqo5peOEUfgA2j` / `team_bGNbBWwra6PVZuM1WULcCW5r` |
| Exact field | Project access, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, and production/preview environment variable names only |
| Value source | Owner-controlled Vercel team and project; existing `.vercel/project.json` for non-secret IDs |
| Reason | The connected Vercel account can see team `malek-virtz`, but `commerce-revenue-autopilot` is not listed/resolvable; Preview deployment, production deployment, logs, and smoke verification are blocked until the existing project is accessible. |
| Expected result | A Preview deployment is created from the canonical branch and can be inspected before production promotion. |
| Verification step after completion | Run `_get_project` / `_get_deployment` or `vercel inspect <preview-deployment-id>`, `uv run python scripts/verify_vercel_access_evidence.py`, `uv run python scripts/verify_deployment_smoke.py <preview-url>`, authenticated API/browser acceptance, then `uv run python scripts/verify_all.py --deployment-url <preview-url>` with the appropriate migration gate inputs. |

## Later Provider Actions

These actions are not the current sequential blocker. Do not perform live activation or payments
without explicit owner confirmation and provider credentials.

| Provider | Exact page | Exact account or project | Exact field | Value source | Reason | Expected result | Verification step after completion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Managed PostgreSQL | Database provider dashboard → Backups / Restore | Production PostgreSQL provider for `DATABASE_URL` | Restored non-production database connection name plus `VERIFY_POSTGRES_URL` and `EXPECTED_MIGRATION_HEAD` environment names | Owner-authorized restored backup target and expected migration marker | Database safety cannot be complete until a real backup restores into a separate destination. | A restored non-production PostgreSQL database is available for validation with the expected migration marker. | Run `uv run python scripts/verify_backup_restore.py` and validate production sample records, migration head, and tenant joins against the restored target. |
| Resend email | Resend Dashboard → Domains and API Keys | Merchant-owned sending domain | `EMAIL_PROVIDER`, `RESEND_API_KEY`, `EMAIL_FROM` environment names | Verified DNS/domain and provider API key | Transactional email cannot be considered active without a verified sender and delivery proof. | Password reset or transactional email can be sent from the production app to an authorized owner address. | Run one authorized password-reset delivery test and record the redacted provider request ID. |
| OpenAI | OpenAI or Vercel AI Gateway dashboard → API keys / gateway project | Owner-approved AI project or gateway | `AI_PROVIDER`, `OPENAI_API_KEY` or gateway credential, `OPENAI_BASE_URL`, `OPENAI_MODEL` environment names | Owner-approved credential, model, budget, and data policy | Live generation cannot be verified without production credentials and policy approval. | Authenticated application generation succeeds under the approved budget and model policy. | Run one authenticated generation through the app and record a redacted request ID plus cost/usage telemetry. |
| Meta / WhatsApp | Meta Business Suite and Meta for Developers → App → WhatsApp / Webhooks | Merchant Meta Business, WABA, phone-number ID, and app | `META_APP_ID`, `META_APP_SECRET`, `META_WHATSAPP_CONFIG_ID`, `META_WHATSAPP_SOLUTION_ID`, `META_OAUTH_REDIRECT_URI` environment names | Business verification, phone verification, permissions, app credentials, and approved templates | WhatsApp cannot be marked active without business/phone verification, webhook acceptance, and an authorized test. | Embedded signup, callback verification, signed webhook, status update, and one authorized sandbox/transactional message succeed. | Run callback verification, signed webhook acceptance/rejection, duplicate-event test, token-failure test, and one authorized message. |
| Media storage / malware scanning | Cloudinary dashboard → Product Environment Credentials, and ClamAV/runtime host settings | Owner-approved media-storage account and malware scanner runtime | `IMAGE_STORAGE_PROVIDER`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_TIMEOUT_SECONDS`, `MALWARE_SCANNER`, `CLAMAV_HOST`, `CLAMAV_PORT`, `MALWARE_SCAN_TIMEOUT_SECONDS` environment names | Owner decision that database-backed media is sufficient, or external Cloudinary/ClamAV runtime credentials and policy | Public media at scale and malware scanning cannot be considered externally active without the owner-approved storage/scanner runtime and acceptance tests. | Uploads persist through the selected storage mode, private retrieval remains signed, clean files pass scanning, malicious files are rejected, and scanner outages fail safely. | Run product upload, private media retrieval, clean-file scan, malware rejection, and scanner-outage tests; record only redacted request/runtime identifiers. |
| Stripe | Stripe Dashboard → Developers → API keys, Webhooks, Products / Prices | Merchant Stripe account | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_GROWTH`, `STRIPE_PRICE_PRO`, `STRIPE_PAYMENT_WEBHOOK_SECRET` environment names | Merchant onboarding, legal approval, live/test keys, prices, and webhook secrets | Card billing/payments remain dormant until merchant onboarding and legal approval are complete. | Stripe checkout/webhooks work while COD remains available. | Run checkout, signed webhook, duplicate-event, cancellation/refund, and inventory consistency tests; real charge only with explicit final confirmation. |
| Sentry alerting | Sentry dashboard → Project settings → Client Keys / DSN and Alerts | Production monitoring project | `SENTRY_DSN` environment name and alert destination names | Owner-created monitoring project and alert routing | External alert delivery is not active without a DSN and destination acceptance. | Runtime errors and health/queue alerts reach the owner-approved incident channel. | Trigger a controlled non-secret test event and verify alert delivery with a redacted event ID. |
### Additional Provider Activation Rows

These rows are part of the later provider-action handoff and are listed separately to preserve the
existing table text.

| Provider | Exact page | Exact account or project | Exact field | Value source | Reason | Expected result | Verification step after completion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Meta social publishing / inbox | Meta Business Suite and Meta for Developers -> App -> Facebook Login, Instagram, Webhooks, and app review | Merchant Facebook Page, Instagram Professional account linked to the Page, and Meta app | `ENABLE_REAL_PUBLISHING`, `META_GRAPH_API_BASE`, `META_GRAPH_API_VERSION`, `META_APP_ID`, `META_APP_SECRET`, `META_OAUTH_REDIRECT_URI`, `META_REQUEST_TIMEOUT_SECONDS`, `META_POLL_INTERVAL_SECONDS`, `META_POLL_TIMEOUT_SECONDS` environment names; per-store OAuth credentials are entered through the app and stored encrypted | Merchant assets, permissions, app review, OAuth connection, and authorized publish/inbox smoke tests | Facebook/Instagram publishing, DMs, and comment handling cannot be marked active without owner-controlled Meta assets and credentialed acceptance. | Authorized Facebook Page and Instagram Business connections report healthy status; one safe publish test and one signed inbound DM/comment webhook test succeed. | Run OAuth callback verification, connection health check, provider-aware publish smoke, signed webhook acceptance/rejection, duplicate-event test, token-failure test, and tenant-isolation checks. |
| Commerce connectors | Shopify Partner/Admin app settings, WooCommerce REST API settings, or merchant generic-commerce API console; application Integrations -> Commerce | Merchant Shopify/WooCommerce/generic store plus production callback URL | `SHOPIFY_APP_API_KEY`, `SHOPIFY_APP_API_SECRET`, `SHOPIFY_OAUTH_REDIRECT_URI`, `SHOPIFY_OAUTH_SCOPES`, `SHOPIFY_API_VERSION`, `COMMERCE_REQUEST_TIMEOUT_SECONDS`, `INTEGRATION_ENCRYPTION_KEY`, `PUBLIC_BASE_URL` environment names; per-store OAuth token, access token, consumer key/secret, and webhook secret are entered through the app and stored encrypted | Commerce import/sync cannot be considered active without merchant store authorization, signed OAuth/callback validation, and signed production webhooks. | Shopify OAuth install or manual store connection health succeeds, catalog/orders sync idempotently, signed webhooks enqueue sync jobs, duplicates are ignored, and cross-tenant access remains denied. | Run Shopify OAuth start/exchange, invalid-HMAC rejection, connection check, sync, signed webhook acceptance/rejection, duplicate-webhook test, failed-provider behavior, and tenant-isolation verification. |
