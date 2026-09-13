# Engineering References

The implementation applies these ideas directly:

- Layered architecture and separation of concerns: domain rules are independent from API and persistence concerns.
- Logical vs. physical architecture: module boundaries remain clear while deployment stays a single artifact.
- Automated unit, integration, API, and end-to-end verification.
- Generative AI patterns: structured outputs, basic RAG, trustworthy generation, dependency injection, bounded reflection, external tool adapters, and guardrails.

Primary external documentation for changing platform behavior:

- [Meta Graph API changelog](https://developers.facebook.com/docs/graph-api/changelog/)
- [Facebook Page Photos](https://developers.facebook.com/docs/graph-api/reference/page/photos/)
- [Instagram Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Meta permissions reference](https://developers.facebook.com/docs/permissions/)

`META_GRAPH_API_VERSION` is configuration, defaulted to `v25.0` after verification on July 22, 2026; revalidate it and all required permissions before every live release.
