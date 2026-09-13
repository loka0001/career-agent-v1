# UI Reference Research

Research date: 2026-09-07  
Decision status: locked for the current V1 productization pass

## Decision

**Primary reference: Gorgias Helpdesk.** Its product grammar is the closest fit for a merchant-facing commerce operations product: a persistent application shell, filtered ticket views, a scannable conversation list, a central timeline/composer, and a contextual customer/commerce rail. Gorgias also connects macros to support and Shopify order actions, making it a stronger functional reference than a generic helpdesk.

**Secondary reference A: Shopify Admin, catalog only.** Reuse its dense product/inventory list-and-detail logic, explicit stock states, bulk operations, and source-of-truth discipline.

**Secondary reference B: Sprout Social, content workflow only.** Reuse its visible draft/needs-approval/scheduled/rejected state model, review queue, activity trail, and calendar transition.

This is a product-grammar decision, not permission to copy branding, source code, proprietary assets, marketing language, or private APIs.

## Method

Eight current products were considered using public first-party help centers and product documentation; seven had usable workflow evidence. Meta's referenced page redirects to login, so it is excluded from scoring. Scores use the weighted rubric in `AGENT.md` (maximum points by column): merchant workflow 25, Inbox UX 20, IA/navigation 15, product/content workflow 15, operational clarity 10, adaptability 5, responsive/accessibility 5, Arabic RTL suitability 5.

Scores are analyst judgments about documented workflow fit, not measured usability. This evidence audit removes unsupported responsive/accessibility and RTL credit: `0*` means unverified, not absent or poor. Shopify receives 2/5 responsive credit for documented desktop/mobile product editing; no candidate has a verified accessibility or Arabic/RTL result. Layout mirroring is our implementation decision and must be tested locally. These changes supersede the earlier totals; Gorgias remains the primary reference.

| Candidate           | Merchant /25 | Inbox /20 | IA /15 | Product/content /15 | Clarity /10 | Adapt /5 | Resp./a11y /5 | RTL /5 |  Total |
| ------------------- | -----------: | --------: | -----: | ------------------: | ----------: | -------: | ------------: | -----: | -----: |
| **Gorgias**         |           25 |        20 |     14 |                  10 |          10 |        5 |            0* |     0* | **84** |
| Shopify Admin       |           25 |         4 |     15 |                  15 |          10 |        5 |             2 |     0* |     76 |
| Intercom            |           18 |        20 |     14 |                   6 |          10 |        5 |            0* |     0* |     73 |
| SleekFlow           |           21 |        17 |     13 |                   8 |           8 |        5 |            0* |     0* |     72 |
| Sprout Social       |           17 |        14 |     13 |                  15 |           9 |        4 |            0* |     0* |     72 |
| respond.io          |           20 |        18 |     13 |                   6 |           9 |        5 |            0* |     0* |     71 |
| Meta Business Suite |            — |         — |      — |                   — |           — |        — |             — |      — |     — |
| Buffer              |           12 |         5 |     12 |                  15 |           9 |        4 |            0* |     0* |     57 |

Rendered evidence inspected on 2026-09-07: the [public Gorgias ticket screenshot](https://attachments.gorgias.help/0bgJ1Q6QZ2vXKOMk/hc/Aa90l7EVvjxJWorj/2026061817-cdb0fcd2-c4b7-4350-8149-f996b07fccb4-ticket.webp) visibly confirms a compact navigation strip, conversation list, central thread/composer, and adjacent customer/order rail. This is desktop evidence only. Other candidates were assessed from the linked documentation, not from authenticated hands-on sessions or verified mobile/RTL screenshots. No reference image is shipped as a product asset.

## Candidate evidence and implications

### Gorgias — selected primary

- Relevant workflow: handle omnichannel customer tickets with merchant context and commerce actions.
- Strongest patterns: persistent navigation; default/shared/private ticket views; priority/channel/time/message-preview scanning; four-region ticket workspace; status, priority, and assignment in the ticket header; central timeline and reply/internal-note composer; right-side customer history and commerce widgets. The public quick-start screenshots and captions expose this hierarchy directly. [Gorgias quick-start guide](https://docs.gorgias.com/en-US/how-to-use-gorgias-a-quick-start-guide-5705504), [ticket handling guide](https://docs.gorgias.com/en-US/handle-incoming-tickets-81832), [ticket-sidebar guide](https://docs.gorgias.com/en-US/tickets-sidebar-101-317554)
- Commerce advantage: connected stores expose customer profiles/order history in the ticket sidebar, and macros can pair a standardized reply with Shopify order actions. [Shopify connection](https://docs.gorgias.com/en-US/connect-shopify-to-gorgias-81814), [macros](https://docs.gorgias.com/en-US/macros-101-81846)
- Weaknesses for this product: it is support-first, not a native social content studio or full catalog manager; the public sources do not establish Arabic/RTL behavior.
- Implementation implication: let this architecture dominate the shell and Inbox. Preserve Commerce Revenue Autopilot's existing content, catalog, opportunity, and approval modules in secondary navigation.

### Shopify Admin — selected catalog secondary

- Relevant workflow: maintain an authoritative product catalog and inventory.
- Strongest patterns: searchable/listable catalog, focused product detail, explicit price/media/variant/tag/metafield structure, bulk operations, CSV paths, and inventory quantities/states. [Products overview](https://help.shopify.com/en/manual/products), [adding and updating products](https://help.shopify.com/en/manual/products/add-update-products), [inventory states](https://help.shopify.com/en/manual/products/inventory/fundamentals/inventory-states)
- Weakness: it is not an omnichannel customer conversation workspace and therefore cannot provide the dominant shell/Inbox grammar.
- Implementation implication: use it only for Products density, filtering, state vocabulary, detail/edit composition, and safe bulk-action placement.

### Intercom

- Relevant workflow: high-volume omnichannel support.
- Strongest patterns: configurable chat/table layouts, bulk actions, status filters, side previews, command menu, internal notes, macros, assignment, and contextual app data. [Inbox explained](https://www.intercom.com/help/en/articles/6258745-the-inbox-explained), [starting a conversation](https://www.intercom.com/help/en/articles/6433002-start-a-conversation-from-the-inbox), [Inbox search and filter](https://www.intercom.com/help/en/articles/6516006-inbox-search-and-filter)
- Weakness: customer support depth is excellent, but merchant catalog/order actions and content operations are less central than in the chosen combination.
- Implementation implication: retain Command-K and accessible table/list ideas already present, but do not dilute the commerce context that makes Gorgias a better primary reference.

### SleekFlow

- Relevant workflow: omnichannel social messaging and conversational commerce.
- Strongest patterns: four-part Inbox—view panel, conversation list, conversation workspace, and contact-information panel—with ownership, collaboration, status, and queue views. [SleekFlow Inbox guide](https://help.sleekflow.io/en_US/getting-started-with-sleekflow-inbox)
- Weakness: public evidence exposes less mature catalog, approval, and operational-depth patterns than the selected references.
- Implementation implication: validates the four-region Inbox model and the importance of contact details beside the active conversation.

### Sprout Social — selected content secondary

- Relevant workflow: create, review, approve, schedule, reject, and recover social posts.
- Strongest patterns: multi-step/multi-user approval, permission-aware submission, a dedicated Needs Approval queue, editable pending work, rejection notes/activity, expiry handling, and transition into the calendar after approval. [Approval workflows](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows), [Publishing Calendar](https://support.sproutsocial.com/hc/en-us/articles/360000121343-How-do-I-use-the-Publishing-Calendar), [Publishing introduction](https://support.sproutsocial.com/hc/en-us/articles/360000576466-Introduction-to-Publishing)
- Weakness: social publishing is strong, but product catalog and merchant order context are not the dominant model.
- Implementation implication: use its state visibility and review/recovery mechanics only inside Content and Calendar.

### respond.io

- Relevant workflow: omnichannel messaging, assignment, collaboration, and AI-assisted replies.
- Strongest patterns: standard/team/custom inboxes, unread/open indicators, chat/call modes, quick close/snooze/assign/collaborate actions, delivery states, channel switching, and a right-side contact/activity/attachment rail. [Inbox overview](https://respond.io/help/inbox), [getting started](https://respond.io/help/inbox/getting-started-with-inbox), [managing conversations](https://respond.io/help/inbox/managing-conversations-in-inbox)
- Weakness: weaker product/catalog and content-approval fit than the selected references.
- Implementation implication: use as corroboration for channel indicators, delivery-state legibility, and responsive progressive disclosure.

### Meta Business Suite

- Relevant workflow: manage native Meta messages, automations, and Facebook/Instagram publishing.
- Evidence unavailable: the [referenced help page](https://www.facebook.com/help/1698046970464236/) redirected to a login page during the 2026-09-07 audit. It cannot establish the current Inbox/Automations layout; the previous score and associated layout claim are withdrawn.
- Weakness: public logged-out documentation exposes less of the current cross-module application architecture than the other candidates; catalog and approval evidence is weaker.
- Implementation implication: preserve familiar channel names and connection states, but do not use its shell as the primary architecture.

### Buffer

- Relevant workflow: draft, request approval, approve/reject, queue, and schedule social posts.
- Strongest patterns: concise approval queue; clear Request Approval, Approve, Reject, Add to Queue, and Schedule Post actions; permission-dependent editing. [Managing and approving drafts](https://support.buffer.com/en-us/articles/managing-and-approving-draft-posts-57li7M8tDA)
- Weakness: narrow publishing focus and minimal merchant Inbox/catalog fit.
- Implementation implication: useful corroboration for straightforward action labels, but Sprout provides the richer approval-state model.

## Patterns to reproduce

- One stable, compact merchant workspace shell with primary work surfaces exposed and secondary tools progressively disclosed.
- Inbox hierarchy: queue filters → scannable conversation list → active timeline/composer → contextual customer/commerce rail.
- Operational state before decoration: unread, overdue, status, priority, channel, assignment, delivery, approval, connection health, and failures remain visible near the action they affect.
- Real context beside the decision: customer identity/history, catalog evidence, and relevant orders without requiring tab switching.
- Explicit lifecycle transitions for content and conversations, including recovery from failed, rejected, expired, or disconnected states.
- Dense list/detail layouts on desktop with deliberate drawer/full-screen or stacked behavior on narrow screens.

## Patterns explicitly not to reproduce

- Candidate names, logos, branded colors, exact copy, illustrations, screenshots, or protected assets.
- Gorgias-only account taxonomy, Intercom product naming, Shopify-specific object names where the domain differs, or private provider behavior.
- Fake filters, assignment controls, bulk actions, analytics, or order buttons without a real API and authorization path.
- English-only fixed left/right assumptions; visual-direction behavior must use logical properties and rendered RTL verification.
- Excessive gradients, glow, rounded cards, decorative AI motifs, or motion unrelated to state.

## Adaptation and technical implications

- The existing modular monolith, typed React API boundary, database source of truth, authorization, tenant isolation, idempotency, and human approval rules remain authoritative.
- The shell and Home already implement much of the required hierarchy. They should be refined incrementally, not rewritten.
- Inbox is the next vertical slice. Its existing list, timeline, suggestion evidence, composer, status change, and delivery-state behavior stay real. The largest reference gap is a contextual customer/commerce rail backed by existing customer-intelligence and order APIs.
- Products should retain real catalog mutations while moving toward a dense Shopify-inspired list/detail arrangement.
- Content should retain real draft/generate/edit/approve/publish behavior while making Sprout-inspired states and recovery paths more explicit.
- Responsive behavior must prioritize the selected conversation and keep its primary action reachable; context becomes stacked or progressively disclosed below desktop width.
- Arabic is the default design constraint: use logical inline/block CSS, mirror directional icons, keep phone/SKU/IDs readable, and render every completed slice in Arabic RTL and English LTR.
