# Dependency Inventory

All versions are pinned in `uv.lock` and `web/package-lock.json`.

## Backend

| Package | Why it exists |
| --- | --- |
| FastAPI, Uvicorn, Pydantic/settings | HTTP API and strict configuration/contracts. |
| SQLAlchemy, Alembic | Authoritative persistence and versioned migrations. |
| Chroma | Small persistent product/policy retrieval index. |
| langchain-openai | One OpenAI-compatible structured-output client. |
| httpx | Meta Graph HTTP calls. |
| Cloudinary | Public HTTPS image storage for real Meta publishing. |
| PyYAML | Versioned prompt loading. |
| pytest/cov, Ruff, mypy | Tests, coverage, lint/format, and type checking. |

## Frontend

| Package | Why it exists |
| --- | --- |
| React/React DOM | UI rendering. |
| React Router | Four-page browser routing. |
| Vite and React plugin | Development and production bundle. |
| TypeScript | Strict browser contracts. |
| Vitest, Testing Library, jsdom | Component and fetch-wrapper tests. |
| ESLint/typescript-eslint | Static checks. |

No general state library, CSS framework, LangGraph, Streamlit, message SDK, or Drive SDK is included.
