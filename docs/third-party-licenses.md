# Third-Party License Notes

This file is an operational inventory, not legal advice. Before commercial distribution, generate and review complete notices from both lockfiles.

- Core Python web/data libraries (FastAPI, Starlette, Pydantic, SQLAlchemy, Alembic, httpx, Uvicorn) use permissive open-source licenses; verify exact package metadata in the lockfile environment.
- Chroma and its transitive local inference/storage dependencies require separate notice review.
- LangChain/OpenAI client libraries and Cloudinary SDK require notice review and provider terms acceptance.
- React, React Router, Vite, TypeScript, Vitest, ESLint, and Testing Library are distributed under permissive open-source licenses; retain their notices.
- Meta, OpenAI-compatible providers, and Cloudinary are external services governed by their current platform terms in addition to SDK licenses.

Suggested release commands:

```bash
uv export --format requirements-txt > /tmp/commerce-python-dependencies.txt
npm --prefix web ls --all > /tmp/commerce-web-dependencies.txt
```
