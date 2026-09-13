# Production Access

Last reviewed: 2026-09-02

## Vercel

- Account observed by CLI: `loka0001`
- Team: `malek-virtz`
- Project: `commerce-revenue-autopilot`
- Project ID: `prj_qd8XsbNvKkxWQvDqo5peOEUfgA2j`
- Team ID: `team_bGNbBWwra6PVZuM1WULcCW5r`

Current connector evidence is recorded in
`artifacts/production-readiness/vercel-access.md`: the connected Vercel account can see the team,
but lists only another project and returns `404 Not Found` for the expected project/deployment.
The historical public URL is reachable but fails the current candidate smoke contract. Treat
deployment control as blocked until project access is restored.

Use least privilege. Remove inactive members and require MFA on human accounts.

Deployment-control environment key names are:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Record names only in repository evidence. Store secret values in GitHub Actions, Vercel, or local
ignored `.env.local` files.

## Merchant Account

Current production merchant email: `merchant@example.com`.

The rotated password is stored locally as a Windows DPAPI-protected file for the current Windows
user:

```powershell
<workspace-tools>\commerce-production-merchant-password.dpapi
```

Do not print the plaintext password in chat, screenshots, logs, documentation, or Git history.
Replace this bootstrap account with a named administrator account after transactional email is live,
then remove the DPAPI file.

## Local Secret Files

Ignored local files may contain secrets:

- `.vercel/.cron-secret.local`
- `.vercel/.env.production.migrate.local`
- `.env*`
- `<workspace-tools>\commerce-production-merchant-password.dpapi`

These files must never be committed.
