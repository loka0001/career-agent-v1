# Backup And Restore

Last reviewed: 2026-08-01

The production database is PostgreSQL. Backups must be handled through the managed database
provider plus verified logical restore drills.

## Before Release

1. Confirm current migration:

```powershell
curl.exe -sS https://commerce-revenue-autopilot.vercel.app/health/ready
```

2. Create or confirm a provider-managed backup snapshot.
3. Run the isolated restore drill against a disposable PostgreSQL database:

```powershell
$env:VERIFY_POSTGRES_URL = '<disposable-postgres-url>'
uv run python scripts/verify_backup_restore.py
```

## Disposable Restore Drill

The restore test creates a temporary schema with representative commerce records, dumps it with
`pg_dump`, drops it, restores it with `pg_restore`, verifies restored row counts, verifies the
expected migration marker, validates order totals, checks inventory/order/product/customer tenant
joins for cross-store leakage, validates background-job rows, and removes only the generated test
schema.

This is a release-gate drill for backup tooling and relational integrity. It is not proof that the
production provider backup policy is active.

Never restore over the active production database. Restore into a separate database, verify tenant
boundaries and key tables, then cut traffic only after approval.

## Minimum Verification

- `organizations`
- `users`
- `stores`
- `products`
- `product_variants`
- `inventory_transactions`
- `orders`
- `order_items`
- `background_jobs`
- `alembic_version`

## Production Restore Acceptance

Production database safety is complete only after an owner-authorized provider backup is restored
into a separate non-production destination and the restored database is validated for:

- migration head matching production;
- core table row presence and expected record samples;
- tenant isolation across organizations, stores, products, customers, orders, and order items;
- inventory transaction continuity;
- background job visibility;
- rollback connection details documented before any traffic switch.
