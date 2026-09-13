# Accessibility and interaction contract

Last verified: 2026-07-30

## Target

The application targets WCAG 2.2 AA for product-owned UI. External provider pages opened
in a new tab are outside this frontend's control.

## Contrast evidence

Calculated WCAG contrast ratios for the final token pairs:

| Pair | Ratio |
| --- | ---: |
| Light ink / canvas | 13.21:1 |
| Light muted / surface | 6.55:1 |
| Light faint / surface | 4.92:1 |
| Light primary button / white text | 7.53:1 |
| Light success text / soft success | 6.65:1 |
| Light warning text / soft warning | 7.40:1 |
| Dark ink / canvas | 15.56:1 |
| Dark muted / surface | 7.84:1 |
| Dark plum link / canvas | 6.68:1 |
| Dark primary button / white text | 5.98:1 |

## Keyboard and focus

- All native form controls have labels or an explicit accessible name.
- Icon-only controls have localized `aria-label` values.
- The mobile drawer moves focus inside, traps Tab/Shift+Tab, closes on Escape, restores
  previous focus, and prevents background scrolling.
- Focus uses the tokenized three-pixel ring and is never removed without replacement.
- Destructive account/store deletion, member/key revocation, provider disconnection,
  store suspension, publishing, order cancellation, and other consequential actions use
  confirmation or stronger proof.
- `prefers-reduced-motion` reduces transitions and animations to an effectively static
  state.

## Semantics and media

- One page-level heading describes every route.
- Alerts use an alert or status role according to urgency.
- Empty states use headings and a real action when one exists.
- Product images provide dimensions, lazy loading, async decoding, and a present `alt`
  attribute; product names remain adjacent text when an image is decorative.
- Tables use stable row semantics or button rows when row selection is the action.

## Automated browser checks

`web/scripts/verify-ui.mjs` fails for:

- a visible input, select, or textarea without a label;
- a visible button or link without an accessible name;
- an image without an `alt` attribute;
- console/page/network errors;
- horizontal overflow;
- a missing mobile navigation;
- a broken drawer focus/Escape interaction;
- missing English LTR headings across reachable routes.

The automated DOM checks complement, but do not replace, manual screen-reader testing
before a broad public launch.
