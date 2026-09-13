# Environment Variable Matrix

Generated: 2026-08-01

Secret values are intentionally omitted.

| Variable | Purpose | Required environments | Current presence | Secret | Provider | Rotation requirement | Validation method |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APP_ENV | Runtime mode | production, preview, test | production+preview present | no | App | no | settings startup |
| APP_SECRET_KEY | Session/signing secret | production, preview | production+preview present | yes | App | rotate on exposure | login/session validation |
| DATABASE_URL | PostgreSQL connection | production, preview | production+preview present | yes | Database | rotate on exposure or staff change | `/health/ready` database |
| VERIFY_POSTGRES_URL | Disposable restore-drill PostgreSQL connection | CI or restore runner | not present in local runtime | yes | Database | rotate on exposure or after drill | backup restore verifier |
| EXPECTED_MIGRATION_HEAD | Expected Alembic migration marker | CI or restore runner | documented as `20260729_0028` | no | Database | update on migration release | backup restore verifier |
| CRON_SECRET | Internal cron/release auth | production | production present | yes | App/Vercel | rotate on exposure | signed drain endpoint |
| INTEGRATION_ENCRYPTION_KEY | Provider credential vault encryption | production | production present | yes | App | rotate with keyring plan | provider credential decrypt test |
| PUBLIC_BASE_URL | Canonical app URL | production, preview | production+preview present | no | App | no | generated links and CORS |
| ALLOWED_ORIGINS | Trusted browser origins | production, preview | production+preview present | no | App | review on domain changes | CORS/browser test |
| COOKIE_SECURE | Secure cookies | production, preview | production+preview present | no | App | no | login cookie flags |
| SEARCH_PROVIDER | Search implementation | production, preview | production+preview present | no | App | no | `/health/ready` search |
| IMAGE_STORAGE_PROVIDER | Media persistence provider | production, preview | production+preview present | no | App | no | upload/retrieval test |
| CLOUDINARY_CLOUD_NAME | External media storage account name | production when Cloudinary active | not present in local runtime | no | Cloudinary | update on account change | upload/retrieval test |
| CLOUDINARY_API_KEY | External media storage API key | production when Cloudinary active | not present in local runtime | yes | Cloudinary | rotate on exposure | upload/retrieval test |
| CLOUDINARY_API_SECRET | External media storage API secret | production when Cloudinary active | not present in local runtime | yes | Cloudinary | rotate on exposure | upload/retrieval test |
| CLOUDINARY_TIMEOUT_SECONDS | External media storage request timeout | production when Cloudinary active | template only | no | Cloudinary | no | upload/retrieval test |
| MALWARE_SCANNER | Malware scanner selector | production when scanner active | template only | no | ClamAV/App | no | upload scan test |
| CLAMAV_HOST | Malware scanner host | production when ClamAV active | template only | no | ClamAV | update on scanner runtime change | upload scan test |
| CLAMAV_PORT | Malware scanner port | production when ClamAV active | template only | no | ClamAV | update on scanner runtime change | upload scan test |
| MALWARE_SCAN_TIMEOUT_SECONDS | Malware scanner timeout | production when ClamAV active | template only | no | ClamAV | no | upload scan test |
| ENABLE_BACKGROUND_WORKER | In-process worker toggle | production, preview | production+preview present | no | App | no | startup mode |
| OPERATOR_EMAILS | Operator access allowlist | production | not present in local runtime | no | App | update on staff change | production readiness warnings |
| RELEASE_SHA | Immutable deployed source identifier | production, preview, CI | not present in local runtime | no | GitHub/Vercel | update every deployment | Git integrity verifier |
| VERCEL_TOKEN | Deployment-control token | local operator or CI | not present in local runtime | yes | Vercel | rotate on exposure or staff change | Vercel CLI/API auth check |
| VERCEL_ORG_ID | Vercel team identifier | local operator or CI | recorded as project metadata only | no | Vercel | update on ownership transfer | Vercel project link check |
| VERCEL_PROJECT_ID | Vercel project identifier | local operator or CI | recorded as project metadata only | no | Vercel | update on project replacement | Vercel project link check |
| AI_PROVIDER | AI provider selector | production, preview | production+preview present | no | App/OpenAI | no | AI application request |
| OPENAI_BASE_URL | Optional gateway endpoint | production | production present | no | OpenAI/Vercel | no | AI application request |
| OPENAI_MODEL | Production model name | production | production present | no | OpenAI/Vercel | review on model changes | AI application request |
| OPENAI_API_KEY | Direct OpenAI credential | production when direct OpenAI active | not present in Vercel listing | yes | OpenAI | rotate per provider policy | AI application request |
| AI_GATEWAY_API_KEY | Vercel AI Gateway credential | production when gateway key active | not present in Vercel listing | yes | Vercel | rotate on exposure | AI application request |
| EMAIL_PROVIDER | Transactional email provider selector | production when email active | not present in Vercel listing | no | Resend/App | update on provider change | password-reset email test |
| RESEND_API_KEY | Transactional email credential | production when email active | not present in Vercel listing | yes | Resend | rotate on exposure | password-reset email test |
| EMAIL_FROM | Verified sender address | production when email active | not present in Vercel listing | no | Resend/DNS | update on sender change | email delivery test |
| ENABLE_REAL_PUBLISHING | Enables real Meta publishing adapters | production when Facebook/Instagram publishing active | production+preview present | no | Meta/App | no | provider-aware publish test |
| META_GRAPH_API_BASE | Meta Graph API base URL | production when Meta active | template only | no | Meta | no | OAuth/webhook/publish test |
| META_GRAPH_API_VERSION | Meta Graph API version | production when Meta active | template only | no | Meta | review on Meta version lifecycle | OAuth/webhook/publish test |
| META_APP_ID | Meta app identifier | production when Meta active | not present in Vercel listing | no | Meta | no | embedded signup/OAuth/webhook test |
| META_APP_SECRET | Meta app secret | production when Meta active | not present in Vercel listing | yes | Meta | rotate on exposure | webhook signature/OAuth test |
| META_WHATSAPP_CONFIG_ID | Embedded Signup config | production when WhatsApp active | not present in Vercel listing | no | Meta | no | embedded signup start |
| META_WHATSAPP_SOLUTION_ID | Meta solution identifier | production when WhatsApp active | not present in Vercel listing | no | Meta | no | embedded signup completion |
| META_OAUTH_REDIRECT_URI | Meta OAuth callback URL | production when Meta active | not present in Vercel listing | no | Meta | update on domain change | OAuth callback verification |
| META_REQUEST_TIMEOUT_SECONDS | Meta API request timeout | production when Meta active | template only | no | Meta/App | no | OAuth/webhook/publish test |
| META_POLL_INTERVAL_SECONDS | Meta publish polling interval | production when Instagram publishing active | template only | no | Meta/App | no | bounded Instagram polling test |
| META_POLL_TIMEOUT_SECONDS | Meta publish polling timeout | production when Instagram publishing active | template only | no | Meta/App | no | bounded Instagram polling test |
| SHOPIFY_APP_API_KEY | Shopify app OAuth API key | production when Shopify OAuth active | template only | no | Shopify | rotate on app replacement | Shopify OAuth start/exchange test |
| SHOPIFY_APP_API_SECRET | Shopify app OAuth API secret | production when Shopify OAuth active | template only | yes | Shopify | rotate on exposure or staff change | Shopify OAuth HMAC/token exchange test |
| SHOPIFY_OAUTH_REDIRECT_URI | Shopify OAuth callback URL | production when Shopify OAuth active | template only | no | Shopify/App | update on domain change | Shopify OAuth redirect/state test |
| SHOPIFY_OAUTH_SCOPES | Requested Shopify OAuth scopes | production when Shopify OAuth active | template only | no | Shopify/App | review on capability changes | Shopify OAuth scope assertion |
| SHOPIFY_API_VERSION | Shopify Admin API version | production when Shopify connector active | template only | no | Shopify/App | review on Shopify version lifecycle | commerce connector smoke |
| COMMERCE_REQUEST_TIMEOUT_SECONDS | Commerce connector request timeout | production when commerce connectors active | template only | no | Commerce/App | no | commerce connector smoke |
| STRIPE_SECRET_KEY | Stripe API credential | production when Stripe active | not present in Vercel listing | yes | Stripe | rotate on exposure | checkout/webhook test |
| STRIPE_WEBHOOK_SECRET | SaaS billing webhook secret | production when billing active | not present in Vercel listing | yes | Stripe | rotate on endpoint change | signed webhook test |
| STRIPE_PRICE_STARTER | Stripe Starter price identifier | production when billing active | not present in Vercel listing | no | Stripe | update on price change | checkout price mapping test |
| STRIPE_PRICE_GROWTH | Stripe Growth price identifier | production when billing active | not present in Vercel listing | no | Stripe | update on price change | checkout price mapping test |
| STRIPE_PRICE_PRO | Stripe Pro price identifier | production when billing active | not present in Vercel listing | no | Stripe | update on price change | checkout price mapping test |
| STRIPE_PAYMENT_WEBHOOK_SECRET | Order payment webhook secret | production when Stripe payments active | not present in Vercel listing | yes | Stripe | rotate on endpoint change | signed webhook test |
| SENTRY_DSN | Error monitoring DSN | production when monitoring active | not present in Vercel listing | yes | Sentry | rotate on exposure | controlled error/alert test |
