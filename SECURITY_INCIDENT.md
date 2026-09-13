# Credential Exposure Response

Local and deployment environment files previously contained production credentials. Code changes
cannot rotate external credentials. Before any production activation, the operator must:

1. Revoke and rotate the Neon/PostgreSQL role password and terminate active database sessions.
2. Generate a new `APP_SECRET_KEY`, deploy it through the secret manager, and invalidate all sessions.
3. Remove or rotate every demo account password and ensure `DEMO_MODE=false`.
4. Rotate provider tokens that may have appeared in archives, logs, screenshots, or deployment files.
5. Scan Git history, release archives, CI artifacts, and deployment logs with Gitleaks.
6. Purge affected artifacts only after preserving the minimum evidence required by the operator's
   incident-response policy.

Do not reuse any value from the removed `.env`, `.vercel.production.env`, or `.neon-deploy.env`
files. Record rotations in the operator's private incident system, not in this repository.
