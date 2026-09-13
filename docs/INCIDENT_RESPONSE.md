# Incident Response

Last reviewed: 2026-08-01

## Severity

- Sev 1: production unavailable, data corruption, confirmed secret exposure, payment or legal risk.
- Sev 2: degraded checkout/COD, failed scheduler, provider outage, repeated 5xx, backup failure.
- Sev 3: isolated feature failure with workaround.

## First 15 Minutes

1. Freeze non-essential deployments.
2. Check `/health/live`, `/health/ready`, Vercel deployment status, and recent logs.
3. Capture timestamps, deployment ID, request IDs, and affected store IDs.
4. If secrets may be exposed, rotate only after a new value is verified and rollback is possible.
5. Do not delete production data during triage.

## Commands

```powershell
curl.exe -sS https://commerce-revenue-autopilot.vercel.app/health/ready
vercel inspect dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx
vercel logs dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx --since 1h
uv run python scripts/verify_deployment_smoke.py https://commerce-revenue-autopilot.vercel.app
```

## Communication

Record what happened, impact, detection source, mitigation, rollback decision, and follow-up owner.
Do not include raw secrets, customer messages, cookies, bearer tokens, or payment data.
