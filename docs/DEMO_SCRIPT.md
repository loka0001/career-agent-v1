# Demonstration script

This script uses only explicitly isolated demo mode. It never represents a provider demo
as a credentialed live integration.

## Prepare

```powershell
uv run python -m scripts.bootstrap_env
uv run python -m scripts.init_local
uv run uvicorn app.main:app --port 8000
npm --prefix web ci
npm --prefix web run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173` and sign in as `merchant@example.com`. Use the one-time password
printed by `bootstrap_env`; never place a reusable demo password in documentation or source.

Confirm the two global labels before presenting:

- `وصول مجاني · بلا بطاقة`
- `بيئة تجريبية · بيانات معزولة`

## Eight-minute product story

1. **Entry** — show the truthful Connect → Operate → Recover narrative. Point out that the
   visual is a capability map, not a fabricated KPI dashboard.
2. **Command Center** — show server-derived decisions, pending work, and zero/real values.
3. **Products** — search/filter the seeded, isolated catalog. Open Add product to show the
   image → review → activation → approval-gated publishing journey.
4. **Inbox** — open an isolated demo conversation. Generate a grounded suggestion and show
   that recommendations use catalog price and stock.
5. **Orders** — create a real order from that conversation. Explain server-calculated
   totals and inventory reservation. Move to pending, choose Prepare collection, and show
   the explicit COD/no-card result. Cancel to demonstrate inventory restoration.
6. **Opportunities** — run the server scan and show reason, confidence, proposed action,
   approval, execution, and recorded outcome.
7. **Automations/content** — show inspectable templates/runs and explicit content approval.
   Do not call demo publishing “live Meta publishing.”
8. **Integrations** — distinguish configured, demo, action required, and unavailable
   providers. Identifiers are masked and secrets never render.
9. **Access & usage** — navigate directly to `/app/billing`; show active free Growth access,
   enforced quotas, no plan cards, and no checkout/portal.
10. **Locale/device** — switch to English LTR, then open the mobile drawer at 390 px.

## Claims to avoid

- Do not claim live Meta, WhatsApp, OpenAI, email, or Stripe without a credentialed smoke
  test for that provider.
- Do not describe seeded products, conversations, or orders as production customer data.
- Do not quote revenue, conversion, or success percentages unless they are visible from
  the current API response.
