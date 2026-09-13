# Three-Person Implementation Ownership

The code is already runnable. Use this ownership map for further implementation without three people editing the same files.

## Person 1 — Product Intelligence and Retrieval

Owns:

- `app/services/product_intelligence.py`
- `app/integrations/ai_provider.py` product analysis/copy methods
- `app/integrations/chroma_store.py`
- `app/application/onboard_product.py`
- `app/repositories/product_repository.py`, `policy_repository.py`
- `app/db/seed.py` and `data/seeds/`
- matching unit/integration tests

First task: connect and evaluate the live vision provider while keeping deterministic CI. Contract: return `ProductRecord`; never change sales/publishing contracts without team review.

## Person 2 — Sales Intelligence

Owns:

- `app/application/assist_customer.py`
- `app/services/sales_assistant.py`
- `app/domain/ranking.py` and reply checks in `validators.py`
- `app/api/routes/sales.py`
- `web/src/features/sales/`
- sales API and inference evaluation tests

First task: expand the evaluation dataset using real anonymized merchant questions. Contract: at most three active, in-stock, within-budget products and valid citations.

## Person 3 — Marketing, Publishing, UI, and Delivery

Owns:

- `app/services/marketing.py`
- `app/application/generate_marketing_pack.py`, `approve_and_publish.py`
- Facebook, Instagram, and image-storage adapters
- product wizard, integration page, shared UI styles
- auth/API composition, Docker, deployment, and publishing tests

First task: configure a staging Cloudinary/Meta account and run the explicit manual acceptance checklist. Contract: no external post without a current server-side approval hash.

## Shared rules

1. Pull the latest main branch before starting.
2. Keep each change within the owned modules where possible.
3. Change `app/domain/models.py`, database migrations, API paths, or shared frontend types only through a reviewed contract change.
4. Add/adjust a test with every behavior change.
5. Run `make test` and `make build` before merging.
6. Merge in this order when contracts change: domain/migration, backend behavior, API tests, then UI.
