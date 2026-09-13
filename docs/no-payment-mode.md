# No-Payment Mode

Last verified: 2026-07-30

The launch policy is server-authoritative:

```dotenv
FREE_ACCESS_MODE=true
BILLING_PROVIDER=disabled
PAYMENT_PROVIDER=cod
```

- Organizations receive active internal Growth access without a trial expiry, card,
  checkout session, or provider billing identifiers.
- Feature entitlements, RBAC, tenant filters, quotas, rate limits, and AI budgets remain
  enforced.
- Subscription checkout and billing portal mutations return `409 Conflict`.
- The production Access & usage page contains no plan grid, card field, upgrade action,
  checkout, or portal.
- Merchant COD orders remain available because customer order collection is separate
  from SaaS access billing.
- Dormant Stripe infrastructure remains intact for a later controlled activation.

Production acceptance verified `provider=internal`, `status=free_access`,
`checkout_available=false`, and `portal_available=false`. The complete policy and
reactivation sequence are in `docs/NO_PAYMENT_ACCESS.md`.

