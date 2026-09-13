---
name: commerce-core-sales-e2e
description: Verify the Commerce Revenue Autopilot customer-message-to-sent-reply journey through the real local UI, API, database, and independent worker, including grounding citations and exactly-once persistence. Use after Inbox, sales-assistant, approval, delivery, or worker changes; do not treat deterministic/demo delivery as live-provider acceptance.
---

# Commerce Core Sales E2E

## Purpose

Produce PASS/FAIL evidence for customer message to Inbox, grounded suggestion, merchant send,
durable worker processing, and persisted outbound status.

## When To Use

- After changes to Inbox UI/API, sales grounding, citations, message approval/send, job handlers,
  external-operation reconciliation, or conversation persistence.
- Before claiming the core local sales journey is release-ready.

## When Not To Use

- Do not run against production or reuse a credential from another checkout.
- Do not claim live OpenAI, Meta, WhatsApp, or delivery-provider acceptance from deterministic
  local adapters.

## Inputs

- A disposable checkout initialized and running through `commerce-clean-bootstrap`.
- API on port 8000, Vite on 5173, and the independent worker running and ready.
- The one-time demo password generated in that checkout.

## Workflow

1. Confirm API and worker readiness. Keep the worker process independent from the API.
2. Expose the one-time password only in the current shell and run the committed journey:

   ```powershell
   $env:UI_DEMO_PASSWORD = Read-Host "One-time local demo password"
   npm --prefix web run verify:journeys
   Remove-Item Env:UI_DEMO_PASSWORD
   ```

3. Interpret only the Inbox portion as this skill's result. It must log in, open a seeded customer
   conversation, request a smart suggestion, display one or more grounding citations, submit the
   merchant-selected reply, and observe exactly one new outbound bubble reaching `Sent`.
4. On failure, preserve browser, API, worker, and job-state evidence without recording the password
   or customer-sensitive payloads. Trace the operation through message, job, audit, and
   external-operation records before changing code.
5. Run focused regressions after a fix:

   ```powershell
   uv run pytest tests/api/test_inbox.py tests/api/test_sales.py tests/integration/test_application_flows.py tests/integration/test_external_operations.py -q
   ```

## Expected Output

- Browser login succeeds and a seeded conversation is visible.
- The suggestion contains authoritative citations and non-empty reply text.
- Sending adds exactly one outbound message.
- The independent worker processes the durable job and persisted status reaches `sent`.
- Browser console, page, request, and response error collections remain empty.

## Failure Conditions

- Missing/foreign-store evidence, fabricated facts, or a suggestion without citations.
- Duplicate outbound rows or jobs, a terminal unknown state represented as sent, or no persisted
  final status.
- The API process executes the supposedly independent worker path.
- Any secret, reusable password, provider token, or raw sensitive payload enters evidence.

## Verification

- Record checkout identity, command, date, exit code, citation count, outbound delta, and final
  status.
- Pair this skill with `commerce-ai-grounding-audit` when prompts, retrieval, or validators changed.
- Pair it with provider-specific acceptance before claiming real delivery.

## Related Files

- `web/scripts/verify-core-journeys.mjs`, `web/src/features/inbox/InboxPage.tsx`
- `app/api/routes/inbox.py`, `app/services/conversations.py`
- `app/application/assist_customer.py`, `app/services/sales_assistant.py`
- `app/services/job_handlers.py`, `app/services/external_operations.py`

## Related Skills

- `commerce-clean-bootstrap`
- `commerce-ai-grounding-audit`
- `commerce-release-gate`
