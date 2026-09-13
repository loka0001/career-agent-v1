# Production Activation

This file lists external actions only. Application code does not need manual editing for
these steps.

## Required Before General Availability

1. Rotate any credential that has ever appeared in logs, chat, screenshots, or repository
   history. Store replacements only in the deployment platform's encrypted environment.
2. Provision a managed PostgreSQL database with TLS, point-in-time recovery, connection
   pooling, and separate production/restore-test projects.
3. Configure the canonical domain, HTTPS, `PUBLIC_BASE_URL`, `ALLOWED_ORIGINS`, DNS, and
   provider callback URLs.
4. Configure an external object-media provider or explicitly accept database media cost
   limits. Provision ClamAV and set `MALWARE_SCANNER=clamav` when untrusted attachments are
   accepted.
5. Deploy `python -m scripts.worker` as an independent always-on service and route its
   health port. Keep the signed Vercel cron as a low-frequency recovery drain.
6. Configure monitoring, Sentry, uptime checks, log retention/redaction, paging, and a
   named incident owner.
7. Schedule managed database backups and complete a restore drill using
   [BACKUP_RESTORE.md](BACKUP_RESTORE.md).
8. Replace the legal placeholders in the Privacy Policy and Terms with approved company,
   country, contact, retention, and subprocessors text.

## Meta And WhatsApp

1. Create or select the production Meta App and add the exact HTTPS OAuth redirect URL.
2. Add `META_APP_ID`, `META_APP_SECRET`, WhatsApp configuration/solution IDs, and webhook
   callback URLs in the deployment environment.
3. Complete Meta Business Verification, App Review, required permissions, data-deletion
   URL registration, privacy URL registration, and webhook subscriptions.
4. Attach merchant-owned Pages, Instagram Professional accounts, WABAs, and phone numbers.
5. Run one controlled test for account selection, inbound message/comment, reply,
   delivery/read state, approved template, post publication, token expiry, disconnect, and
   repeated webhook delivery.

## Email, AI, And Payments

1. Verify a sending domain with the chosen transactional email provider; configure its API
   key, sender, bounce/complaint handling, and deliverability monitoring.
2. Provision the production AI provider key, approve the model and regional data policy,
   set current token prices, and run the optional credentialed eval suite.
3. Stripe remains intentionally frozen while no-payment access is active. To activate it,
   accept the provider terms, create production products/prices, configure billing and
   payment webhook secrets, enable customer portal settings, disable
   `FREE_ACCESS_MODE`, and run payment/refund/past-due/cancellation smoke tests.
4. Until that separately approved activation, keep `FREE_ACCESS_MODE=true`,
   `BILLING_PROVIDER=disabled`, and `PAYMENT_PROVIDER=cod` where COD is operationally
   supported. Free access must continue to preserve quotas, roles, tenant isolation,
   and audit policy.
