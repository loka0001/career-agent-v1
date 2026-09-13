# Privacy And Retention

This is an engineering policy, not a compliance certification. Replace legal placeholders
in the in-app Privacy Policy and Terms before general availability.

## Implemented Controls

- Store and customer JSON export.
- Account, store, and customer deletion requests with status tracking.
- Configurable message/media retention and durable cleanup jobs.
- Meta signed data-deletion callback and public confirmation code.
- Consent and opt-in/opt-out history.
- Provider credentials, API keys, sessions, and OAuth transactions removed/revoked during
  eligible deletion workflows.
- Private customer media with expiring signed URLs.
- Audited sensitive operations.

## Deletion Rules

Eligible profile, conversation, message, media, token, and provider-connection data is
deleted or anonymized after the configured grace period. Financial/order/payment records
that must be retained for accounting are preserved with customer PII removed. Audit events
needed for security and legal defense retain minimal identifiers and never retain raw
provider secrets.

Deletion is asynchronous. Operators monitor the durable request/job state and must not
claim completion before the request status is `completed`.

## Tracking And Cookies

The application uses secure session and CSRF cookies. The website widget records behavioral
events only after explicit tracking consent. A merchant must configure its visible cookie
notice and lawful basis before enabling tracking on its site.

## Operational Requirements

- Approve retention periods for every launch country and data category.
- Publish the controller/company identity, contact details, subprocessors, transfer terms,
  and complaint route.
- Test export and deletion quarterly.
- Include backups and provider copies in the deletion/expiry policy.
- Record legal holds explicitly; never silently disable deletion.
