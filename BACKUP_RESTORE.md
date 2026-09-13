# Backup And Restore

## Policy

Use managed PostgreSQL point-in-time recovery plus daily logical backups. Encrypt backups,
restrict them to the operations role, store them in a separate account/region, and apply a
documented retention period. Application exports are not database backups.

Recommended minimum:

- PITR retention: 7-30 days according to plan and law.
- Daily custom-format `pg_dump`.
- Weekly integrity check.
- Quarterly restore drill.
- Backup before every schema release.

## Logical Backup

Run from a trusted operations host with PostgreSQL client tools:

```bash
pg_dump "$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="commerce-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Hash and encrypt the archive before off-host transfer. Never write it inside the source
repository or attach it to tickets/chat.

## Restore Drill

1. Create a new empty PostgreSQL database with the same major version and extensions.
2. Restore into that new database:

```bash
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-acl commerce.dump
```

3. Run `alembic current`, `alembic upgrade head`, `/health/ready`, tenant-isolation tests,
   row counts for stores/orders/events, and a read-only application smoke test.
4. Compare sampled checksums and the recorded backup timestamp.
5. Destroy the drill database according to retention policy.

`scripts/verify_backup_restore.py` performs a safe CI smoke test by creating a random
schema, backing up one integrity fixture, deleting it, restoring it, checking its hash,
and dropping the schema. It requires `VERIFY_POSTGRES_URL`, `pg_dump`, and `pg_restore`.

## Disaster Recovery

Restore to a new database or provider branch, validate it, stop writes, and then update the
deployment secret. Do not restore over the active database. Rotate database credentials
after the event and record recovery point objective, recovery time, lost-write window, and
verification evidence.
