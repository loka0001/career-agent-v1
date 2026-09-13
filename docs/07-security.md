# Security

## Implemented controls

- Secrets are accepted only from environment variables; `.env` is ignored.
- `scripts.bootstrap_env` generates a random application key and scrypt password hash.
- The session is HMAC-signed, time-limited, HttpOnly, SameSite Lax, and Secure in production.
- A double-submit CSRF token is required for authenticated state changes.
- Every business query is scoped to the active store membership. Cross-tenant API tests cover
  customers, orders, opportunities, automations, content, and team resources.
- RBAC is checked server-side for analyst, agent, marketer, admin, and owner roles. Role and
  store values supplied by the browser are never trusted.
- Image MIME, magic bytes, extension, size, and UUID storage names are validated.
- Pydantic rejects extra fields and limits important string/list sizes.
- Request IDs and security headers are attached by middleware.
- Structured logs redact common token, key, authorization, and password patterns.
- Integration credentials stored per channel are encrypted with Fernet using a key derived
  from `APP_SECRET_KEY`; APIs return only configured state and masked identifiers.
- WhatsApp and Meta webhook payloads require a constant-time HMAC-SHA256 signature check before
  parsing. Event IDs are persisted to make repeated delivery idempotent.
- WhatsApp free-form sends are blocked outside the 24-hour service window, and every send path
  enforces the customer's per-channel consent.
- Approval is a server record containing actor, time, content version, and SHA-256 hash.
- Team role changes prevent removing or demoting the last owner. Temporary credentials are
  returned once and are not stored in plaintext.
- API keys are stored as hashes, scoped, shown once, and revocable.
- Public website and authentication-sensitive endpoints use database-backed fixed-window rate
  limits in `rate_limit_buckets`, so limits are shared across application instances that use the
  same production PostgreSQL database.
- Subscription limits are enforced in the service layer across the whole organization, including
  channels, team members, conversations, AI operations, posts, and automations.
- React renders user content as escaped text; no raw HTML rendering is used.

## Production checklist

- Use HTTPS and set `COOKIE_SECURE=true`.
- Set a strong `APP_SECRET_KEY`; never use the development fallback.
- Restrict `ALLOWED_ORIGINS` to the production origin.
- Keep platform or WAF rate limits in front of high-cost authenticated AI and publish endpoints as
  defense in depth; application-level database rate limits already protect public website and auth
  abuse paths.
- Rotate Meta/OpenAI/Cloudinary secrets and grant the minimum permissions.
- Use a public Cloudinary HTTPS URL for real Meta publishing.
- Back up the SQL database before every migration.
- Do not log customer message bodies in production observability exports.

## Residual risks and launch blockers

- The application-level rate limiter depends on the primary database. Add platform/WAF limits before
  high-volume launch so abuse throttling still works during database degradation.
- Local SQLite development remains a single-instance topology. Use PostgreSQL and a durable
  distributed worker before running multiple production application instances.
- Team invitations currently expose a temporary password once in the authenticated owner UI; no
  email delivery or forced first-login password rotation is implemented.
- `npm audit` reports the React Router RSC Action CSRF advisory. This product is a Vite client-side
  SPA and does not use React Server Components, server actions, or React Router server handlers,
  so the vulnerable surface is not present. Keep the dependency current and re-evaluate if SSR or
  server actions are introduced.
- Provider app review, token lifetime, account permissions, webhook delivery, and real publishing
  must be validated with merchant-owned accounts before production launch.
