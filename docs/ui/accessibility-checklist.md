# Accessibility Checklist

Last verified: 2026-08-08

The implementation target is WCAG 2.2 AA for product-owned UI. Detailed contrast and
interaction evidence is in `docs/ui/accessibility.md`.

## Verified

- [x] Semantic page heading on every primary route.
- [x] Native labels or accessible names for visible form controls.
- [x] Localized accessible names for icon-only buttons and links.
- [x] Visible tokenized keyboard focus.
- [x] Mobile drawer focus entry, Tab containment, Escape close, and focus restoration.
- [x] Alert/status roles selected by urgency.
- [x] Image `alt` attributes present.
- [x] Light and dark foreground/background token pairs meet AA contrast.
- [x] Arabic RTL and English LTR preserve readable numbers, dates, and actions.
- [x] Reduced-motion preference suppresses nonessential transitions.
- [x] No unintended horizontal overflow at 390, 768, or 1440 pixels.
- [x] Production browser run found no unnamed visible controls, console/page errors,
      failed requests, or HTTP errors across 20 authenticated routes.
- [x] Logical-property lint blocks RTL/LTR regressions in all authored CSS.
- [x] Catalog table and customer master-detail views pass the desktop overflow gate.

## Manual Launch Follow-up

- [ ] Complete a screen-reader pass with NVDA and VoiceOver before a broad public
      marketing launch.
- [ ] Recheck provider-owned embedded flows when real merchant accounts are connected.
- [ ] Repeat keyboard and contrast review after any design-token or navigation change.
