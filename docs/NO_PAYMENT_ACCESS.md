# No-payment access policy

Last updated: 2026-07-30

## Current launch policy

`FREE_ACCESS_MODE=true` is the server-authoritative launch setting.

- New and returning organizations receive the internal Growth entitlement with status
  `active`, no trial expiry, no provider customer/subscription identifiers, and no
  cancellation date.
- Existing internal trials are reconciled at login and subscription reads.
- Feature entitlements, role checks, tenant filters, resource limits, monthly usage
  quotas, AI budgets, and rate limits remain enforced.
- Plan-change checkout and billing-portal endpoints return `409 Conflict` with
  `free_access=true`; no checkout URL is created.
- The UI removes pricing, upgrade, checkout, and portal actions, while retaining a direct
  Access & usage route for quota transparency.
- A `free_access_granted` audit event is written once per organization.

## Two payment domains

SaaS access billing and merchant order collection are separate:

- `BILLING_PROVIDER=disabled` means the merchant is not charged to use this product.
- `PAYMENT_PROVIDER=cod` means a merchant can prepare customer orders for cash on
  delivery. The server changes an eligible order to confirmed/awaiting-cash without
  creating a card link.
- Dormant Stripe subscription and order-payment code, signed webhooks, migrations, and
  tests remain intact, but no Stripe UI is exposed in free mode.

## Safe activation later

To activate paid SaaS access:

1. Complete product/legal/finance approval.
2. Configure Stripe products, prices, webhook secret, return URLs, and incident ownership.
3. Pass provider sandbox and signed-webhook acceptance tests.
4. Set `BILLING_PROVIDER=stripe`.
5. Set `FREE_ACCESS_MODE=false` only in the same controlled release.
6. Verify entitlements and legacy free organizations before exposing pricing or checkout.

Changing only the frontend is insufficient and unsupported.

## Evidence

`tests/api/test_no_payment_mode.py` proves:

- active Growth access without a trial;
- checkout/portal refusal and absence of checkout details;
- tenant isolation and owner RBAC;
- quota enforcement at the Growth ceiling;
- reconciliation of an existing trial;
- one-time audit recording.
