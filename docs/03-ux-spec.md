# UX Specification

## Product promise

“Add a product once, create its content, publish it, and use its data to turn customer questions into sales opportunities.”

## Merchant journey

1. Sign in at `/login`.
2. Open `/app/products/new` and enter facts plus JPEG/PNG/WebP.
3. Wait for structured analysis; a progress state remains visible.
4. Review editable name, category, price, stock, features, benefits, and description.
5. Activate the reviewed product.
6. Generate separate Facebook and Instagram previews.
7. Edit content; any edit invalidates earlier approval.
8. Approve explicitly, confirm publishing, and inspect each platform result.

## Customer-assistance journey

1. Open `/app/sales` and enter a customer message.
2. Inspect the collapsible structured need.
3. Review at most three available product cards and short ranking reasons.
4. Copy the grounded reply and inspect stable product/policy references.
5. See explicit no-match or out-of-domain text when evidence is insufficient.

## Required states implemented

- Loading, empty, error, validation warning, disabled action, and success states.
- Demo/real/disabled integration modes.
- Per-platform publish success or failure.
- Retry with API idempotency protection.
- Responsive single-column layout below 800px.

## Accessibility

Semantic labels, visible focus rings, keyboard-operable controls, AA-oriented colors, meaningful alerts, reduced-motion support, and true document `dir` switching are used. React escapes user text by default.
